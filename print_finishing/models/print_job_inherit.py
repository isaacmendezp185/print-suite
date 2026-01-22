
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PrintJob(models.Model):
    _inherit = 'print.job'

    # -----------------------------
    #   ACABADOS
    # -----------------------------
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

    # -----------------------------
    #   VÍNCULOS MRP
    # -----------------------------
    bom_id = fields.Many2one('mrp.bom', string='BoM (job)', copy=False)
    production_id = fields.Many2one('mrp.production', string='Orden de fabricación', copy=False)

    # -----------------------------
    #   CÁLCULO TOTALES ACABADOS
    # -----------------------------
    @api.depends('finishing_line_ids.cost_line', 'finishing_line_ids.hours')
    def _compute_finishing_totals(self):
        for job in self:
            job.total_finishing_hours = sum(job.finishing_line_ids.mapped('hours'))
            job.total_finishing_cost = sum(job.finishing_line_ids.mapped('cost_line'))

    # -----------------------------
    #   COSTEO (EXTIENDE AL DE MÓDULO DE COSTEO)
    # -----------------------------
    def action_estimate_costs(self):
        res = super().action_estimate_costs()
        for job in self:
            finishing_cost = sum(job.finishing_line_ids.mapped('cost_line'))
            job.write({
                'cost_finishing': finishing_cost,
                'cost_total': (job.cost_material or 0.0)
                              + (job.cost_ink or 0.0)
                              + (job.cost_machine or 0.0)
                              + (finishing_cost or 0.0),
            })
        return res

    # -----------------------------
    #   UTILIDADES DE CENTRO DE TRABAJO
    # -----------------------------
    def _find_default_workcenter(self, center_type):
        """Encuentra un workcenter por print_center_type para casos sin máquina."""
        return self.env['mrp.workcenter'].search([('print_center_type', '=', center_type)], limit=1)

    def _build_job_operations(self):
        """
        Devuelve lista de dicts con operaciones para este job:
        - Impresión (si hay máquina impresora)
        - Una operación por cada línea de acabado
        """
        self.ensure_one()
        ops = []
        seq = 1

        # 1) Operación de IMPRESIÓN
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

        # 2) Operaciones de ACABADOS
        for line in self.finishing_line_ids.sorted('sequence'):
            wc = line.machine_id.workcenter_id or self._find_default_workcenter(line.center_type)
            if not wc:
                raise UserError(_('No se encontró un Centro de trabajo para el acabado %s.') % (line.operation,))
            op_label = dict(line._fields['operation'].selection).get(line.operation, line.operation)
            ops.append({
                'name': _('Acabado: %s') % op_label,
                'workcenter_id': wc.id,
                'sequence': seq,
            })
            seq += 1

        if not ops:
            raise UserError(_('No hay operaciones para crear (agrega máquina de impresión o al menos una línea de acabado).'))

        return ops

    # -----------------------------
    #   PRODUCTO DEL JOB PARA MRP
    # -----------------------------
    def _ensure_job_product(self):
        """Crea un producto genérico si el job no tiene producto asignado."""
        self.ensure_one()
        if self.product_id:
            return self.product_id

        tmpl = self.env['product.template'].create({
            'name': 'Trabajo de impresión',
            'type': 'consu',  # Usa 'product' si deseas inventariarlo
        })
        product = self.env['product.product'].create({'product_tmpl_id': tmpl.id})

        self.write({
            'product_id': product.id,
            'product_uom_id': product.uom_id.id,
            'product_qty': self.product_qty or 1.0
        })
        return product

    # -----------------------------
    #   BoM (Community: sin operaciones)
    # -----------------------------
    def _create_bom_for_job(self, product):
        """
        Crea BoM simple (Community NO tiene mrp.bom.operation).
        En Enterprise podríamos añadir operaciones, pero aquí se omite.
        """
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
        self.write({'bom_id': bom.id})
        return bom

    # -----------------------------
    #   HORAS ESPERADAS POR OPERACIÓN
    # -----------------------------
    def _compute_expected_hours(self):
        """Devuelve mapping {nombre_operacion: horas_esperadas} para impresión y acabados."""
        self.ensure_one()
        hours_map = {}

        # Impresión
        if self.machine_id and (self.machine_id.machine_role == 'printer'):
            hours_machine = 0.0
            if (self.machine_id.speed_m2_h or 0.0) > 0 and (self.area_m2 or 0.0) > 0:
                speed_factor = {
                    'draft': 1.05,
                    'standard': 1.0,
                    'high': 0.9,
                }.get(self.quality or 'standard', 1.0)
                eff_speed_m2_h = (self.machine_id.speed_m2_h or 0.0) * speed_factor
                if eff_speed_m2_h > 0:
                    hours_machine = self.area_m2 / eff_speed_m2_h
            hours_map[_('Impresión')] = hours_machine

        # Acabados
        for line in self.finishing_line_ids:
            op_label = dict(line._fields['operation'].selection).get(line.operation, line.operation)
            name = _('Acabado: %s') % op_label
            hours_map[name] = line.hours or 0.0

        return hours_map

    # -----------------------------
    #   CREAR MO + (opcional) WOs
    # -----------------------------
    def action_create_mo_with_wos(self):
        """
        Flujo Community:
        - Garantiza producto
        - Crea BoM sin operaciones
        - Crea MO y confirma
        - Si existe 'mrp.workorder' en la instancia: crea WOs manualmente con base en _build_job_operations()
          y ajusta duración esperada (si el campo existe). Si no existe, solo deja la MO creada.
        """
        for job in self:
            if job.production_id:
                raise UserError(_('Este trabajo ya tiene una Orden de Fabricación: %s') % (job.production_id.name,))

            product = job._ensure_job_product()
            if not job.product_qty or job.product_qty <= 0:
                job.product_qty = 1.0

            bom = job._create_bom_for_job(product)

            mo_vals = {
                'product_id': product.id,
                'product_qty': job.product_qty,
                'product_uom_id': job.product_uom_id.id or product.uom_id.id,
                'origin': job.name,
                'company_id': job.company_id.id,
                'bom_id': bom.id,
            }
            if job.deadline_date:
                mo_vals['date_deadline'] = job.deadline_date

            mo = self.env['mrp.production'].create(mo_vals)

            # Confirmar MO (Community lo soporta)
            mo.action_confirm()

            # Si hay modelo de Work Orders en esta instancia, crear WOs manualmente
            if 'mrp.workorder' in self.env:
                ops = job._build_job_operations()
                for op in ops:
                    wo = self.env['mrp.workorder'].create({
                        'production_id': mo.id,
                        'name': op['name'],
                        'workcenter_id': op['workcenter_id'],
                        'sequence': op['sequence'],
                    })
                    # Ajustar duración si el campo existe
                    if 'duration_expected' in wo._fields:
                        hours_map = job._compute_expected_hours()
                        h = hours_map.get(op['name'])
                        if h and h > 0:
                            wo.write({'duration_expected': int(round(h * 60))})
            else:
                # Sin WOs en Community, informar en chatter
                mo.message_post(body=_(
                    'Tu instancia no tiene "Work Orders". Se creó la MO sin WOs. '
                    'Si activas Work Orders, se generarán automáticamente en este paso.'
                ))

            job.write({'production_id': mo.id})
            job.message_post(body=_('Se creó la Orden de Fabricación %s.') % (mo.name,))
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
