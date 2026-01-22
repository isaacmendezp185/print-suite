
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


# ---------------------------------------------------------
#   EXTENSIÓN DEL MODELO print.job PARA ACABADOS + MRP
# ---------------------------------------------------------
class PrintJob(models.Model):
    _inherit = 'print.job'

    # Líneas de acabado
    finishing_line_ids = fields.One2many(
        'print.job.finishing', 'job_id', string='Líneas de acabado'
    )

    total_finishing_hours = fields.Float(
        string='Horas de acabado', compute='_compute_finishing_totals', store=False
    )
    total_finishing_cost = fields.Monetary(
        string='Costo de acabados', currency_field='currency_id',
        compute='_compute_finishing_totals', store=False
    )

    # Enlaces con MRP
    bom_id = fields.Many2one('mrp.bom', string='BoM (job)', copy=False)
    production_id = fields.Many2one('mrp.production', string='Orden de fabricación', copy=False)


    # ---------------------------------------------------------
    #   TOTALES DE ACABADOS
    # ---------------------------------------------------------
    @api.depends('finishing_line_ids.cost_line', 'finishing_line_ids.hours')
    def _compute_finishing_totals(self):
        for job in self:
            job.total_finishing_hours = sum(job.finishing_line_ids.mapped('hours'))
            job.total_finishing_cost  = sum(job.finishing_line_ids.mapped('cost_line'))


    # ---------------------------------------------------------
    #   REDEFINIR COSTEO PARA SUMAR ACABADOS
    # ---------------------------------------------------------
    def action_estimate_costs(self):
        res = super().action_estimate_costs()

        for job in self:
            finishing_cost = sum(job.finishing_line_ids.mapped('cost_line'))
            job.write({
                'cost_finishing': finishing_cost,
                'cost_total': (job.cost_material or 0.0) +
                              (job.cost_ink or 0.0) +
                              (job.cost_machine or 0.0) +
                              (finishing_cost or 0.0),
            })
        return res


    # ---------------------------------------------------------
    #   SELECTOR DE CENTRO DE TRABAJO
    # ---------------------------------------------------------
    def _find_default_workcenter(self, center_type):
        wc = self.env['mrp.workcenter'].search([
            ('print_center_type', '=', center_type)
        ], limit=1)
        return wc


    # ---------------------------------------------------------
    #   ARMADO DE OPERACIONES PARA LA BoM
    # ---------------------------------------------------------
    def _build_job_operations(self):
        self.ensure_one()
        ops = []
        seq = 1

        # --- Impresión ---
        if self.machine_id and (self.machine_id.machine_role == 'printer'):
            wc = self.machine_id.workcenter_id or self._find_default_workcenter(self.machine_id.center_type)
            if not wc:
                raise UserError(_('No se encontró un Centro de trabajo para la operación de impresión.'))

            ops.append({
                'name': _('Impresión'),
                'workcenter_id': wc.id,
                'sequence': seq,
            })
            seq += 1

        # --- Acabados ---
        for line in self.finishing_line_ids.sorted('sequence'):
            wc = line.machine_id.workcenter_id or self._find_default_workcenter(line.center_type)
            if not wc:
                raise UserError(_('No se encontró un Centro de trabajo para el acabado %s.') % line.operation)

            op_label = dict(line._fields['operation'].selection).get(line.operation, line.operation)

            ops.append({
                'name': _('Acabado: %s') % op_label,
                'workcenter_id': wc.id,
                'sequence': seq,
            })
            seq += 1

        if not ops:
            raise UserError(_('No hay operaciones para crear (agrega máquina o líneas de acabado).'))

        return ops


    # ---------------------------------------------------------
    #   PRODUCTO DEL JOB PARA MRP
    # ---------------------------------------------------------
    def _ensure_job_product(self):
        self.ensure_one()
        if self.product_id:
            return self.product_id

        tmpl = self.env['product.template'].create({
            'name': 'Trabajo de impresión',
            'type': 'consu',
        })
        product = self.env['product.product'].create({
            'product_tmpl_id': tmpl.id
        })

        self.write({
            'product_id': product.id,
            'product_uom_id': product.uom_id.id,
            'product_qty': self.product_qty or 1.0
        })

        return product


    # ---------------------------------------------------------
    #   CREAR BoM + OPERACIONES MRP
    # ---------------------------------------------------------
    def _create_bom_for_job(self, product):
        self.ensure_one()

        if self.bom_id:
            return self.bom_id

        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_id': product.id,
            'type': 'normal',
            'code': self.name or 'JOB',
            'company_id': self.company_id.id,
        })

        # Crear operaciones
        ops = self._build_job_operations()

        for op in ops:
            self.env['mrp.bom.operation'].create({
                'name': op['name'],
                'workcenter_id': op['workcenter_id'],
                'sequence': op['sequence'],
                'bom_id': bom.id,
            })

        self.write({'bom_id': bom.id})
        return bom


    # ---------------------------------------------------------
    #   CÁLCULO DE HORAS ESPERADAS
    # ---------------------------------------------------------
    def _compute_expected_hours(self):
        self.ensure_one()
        hours_map = {}

        # Impresión
        if self.machine_id and (self.machine_id.machine_role == 'printer'):
            hours = 0.0
            if (self.machine_id.speed_m2_h or 0) > 0 and (self.area_m2 or 0) > 0:

                speed_factor = {
                    'draft': 1.05,
                    'standard': 1.0,
                    'high': 0.9,
                }.get(self.quality or 'standard', 1.0)

                eff_speed = self.machine_id.speed_m2_h * speed_factor
                if eff_speed > 0:
                    hours = self.area_m2 / eff_speed

            hours_map[_('Impresión')] = hours

        # Acabados
        for line in self.finishing_line_ids:
            op_label = dict(line._fields['operation'].selection).get(line.operation, line.operation)
            hours_map[_('Acabado: %s') % op_label] = line.hours or 0.0

        return hours_map


    # ---------------------------------------------------------
    #   CREAR MO + WOs
    # ---------------------------------------------------------
    def action_create_mo_with_wos(self):
        for job in self:
            if job.production_id:
                raise UserError(_('Este trabajo ya tiene una Orden de Fabricación.'))

            product = job._ensure_job_product()
            if not job.product_qty or job.product_qty <= 0:
                job.product_qty = 1.0

            bom = job._create_bom_for_job(product)

            mo = self.env['mrp.production'].create({
                'product_id': product.id,
                'product_qty': job.product_qty,
                'product_uom_id': job.product_uom_id.id,
                'origin': job.name,
                'company_id': job.company_id.id,
                'bom_id': bom.id,
            })

            if job.deadline_date:
                mo.write({'date_deadline': job.deadline_date})

            mo.action_confirm()
            if hasattr(mo, 'button_plan'):
                mo.button_plan()

            # Ajustar duración de WOs
            hours_map = job._compute_expected_hours()

            for wo in mo.workorder_ids:
                h = hours_map.get(wo.name)
                if h and h > 0:
                    wo.write({'duration_expected': int(round(h * 60))})

            job.write({'production_id': mo.id})
            job.message_post(body=_('Se generó y planificó la OF %s') % mo.name)

        return True


    def action_open_mo(self):
        self.ensure_one()
        if not self.production_id:
            raise UserError(_('No hay Orden de Fabricación vinculada.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Orden de Fabricación'),
            'res_model': 'mrp.production',
            'res_id': self.production_id.id,
            'view_mode': 'form',
        }
