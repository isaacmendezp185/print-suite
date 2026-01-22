
from odoo import api, fields, models

class PrintJob(models.Model):
    _inherit = 'print.job'

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

    @api.depends('finishing_line_ids.cost_line', 'finishing_line_ids.hours')
    def _compute_finishing_totals(self):
        for job in self:
            job.total_finishing_hours = sum(job.finishing_line_ids.mapped('hours'))
            job.total_finishing_cost  = sum(job.finishing_line_ids.mapped('cost_line'))

    # Extiende el botón de costeo del módulo de costeo
    def action_estimate_costs(self):
        # Llama primero al cálculo de Material/Tinta/Máquina (super)
        res = super().action_estimate_costs()
        for job in self:
            finishing_cost = sum(job.finishing_line_ids.mapped('cost_line'))
            # Actualiza campo estándar del job y recalcula total
            job.write({
                'cost_finishing': finishing_cost,
                'cost_total': (job.cost_material or 0.0) +
                              (job.cost_ink or 0.0) +
                              (job.cost_machine or 0.0) +
                              (finishing_cost or 0.0),
            })
        return res


# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PrintJob(models.Model):
    _inherit = 'print.job'

    bom_id = fields.Many2one('mrp.bom', string='BoM (job)', copy=False)
    production_id = fields.Many2one('mrp.production', string='Orden de fabricación', copy=False)

    def _find_default_workcenter(self, center_type):
        """Encuentra un workcenter por print_center_type para casos sin máquina."""
        wc = self.env['mrp.workcenter'].search([('print_center_type', '=', center_type)], limit=1)
        return wc

    def _build_job_operations(self):
        """
        Arma la lista de operaciones (dicts) para crear mrp.bom.operation:
        - 1) Impresión (si aplica)
        - 2) Acabados (cada línea de finishing)
        """
        self.ensure_one()
        ops = []
        seq = 1

        # 1) Operación de IMPRESIÓN (si machine_id existe y es impresora)
        if self.machine_id and (self.machine_id.machine_role in ('printer',)):
            wc = self.machine_id.workcenter_id or False
            if not wc:
                wc = self._find_default_workcenter(self.machine_id.center_type)
            if not wc:
                raise UserError(_('No se encontró un Centro de trabajo para la operación de impresión.'))

            # Nombre claro de operación
            ops.append({
                'name': _('Impresión'),
                'workcenter_id': wc.id,
                'sequence': seq,
            })
            seq += 1

        # 2) Operaciones de ACABADOS (cada línea)
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
            raise UserError(_('No hay operaciones para crear: agrega máquina de impresión o al menos una línea de acabado.'))
        return ops

    def _ensure_job_product(self):
        """Garantiza un product para el MO. Si no hay, crea un genérico 'Trabajo de impresión' (consumible)."""
        self.ensure_one()
        if self.product_id:
            return self.product_id

        tmpl_vals = {
            'name': 'Trabajo de impresión',
            'type': 'consu',  # 'product' si quieres inventariarlo
        }
        product = self.env['product.product'].create({'product_tmpl_id': self.env['product.template'].create(tmpl_vals).id})
        self.write({'product_id': product.id, 'product_uom_id': product.uom_id.id, 'product_qty': self.product_qty or 1.0})
        return product

    def _create_bom_for_job(self, product):
        """Crea la BoM para el job (si no existe) y sus operaciones base (sin tiempos, los afinamos en los WOs)."""
        self.ensure_one()
        if self.bom_id:
            return self.bom_id

        bom_vals = {
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_id': product.id,
            'type': 'normal',
            'code': self.name or 'JOB',
            'company_id': self.company_id.id,
        }
        bom = self.env['mrp.bom'].create(bom_vals)

        # Crear operaciones asociadas a la BoM
        ops = self._build_job_operations()
        op_model = self.env['mrp.bom.operation']
        for op in ops:
            op_model.create(dict(op, bom_id=bom.id))

        self.write({'bom_id': bom.id})
        return bom

    def _compute_expected_hours(self):
        """Devuelve mapping nombre_operacion -> horas_esperadas para impresión y acabados."""
        self.ensure_one()
        hours_map = {}

        # Impresión
        if self.machine_id and (self.machine_id.machine_role in ('printer',)):
            hours_machine = 0.0
            if (self.machine_id.speed_m2_h or 0.0) > 0 and (self.area_m2 or 0.0) > 0:
                # Factor por calidad (coherente con print_costing_engine)
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

    def action_create_mo_with_wos(self):
        """
        Crea MO + WOs:
        - Garantiza producto del job
        - Crea BoM con operaciones (impresión + acabados)
        - Crea MO con esa BoM, confirma y planifica (genera WOs)
        - Ajusta duración esperada de cada WO según horas calculadas
        """
        for job in self:
            if job.production_id:
                raise UserError(_('Este trabajo ya tiene una Orden de Fabricación: %s') % (job.production_id.name,))

            product = job._ensure_job_product()
            if not job.product_qty or job.product_qty <= 0:
                job.product_qty = 1.0

            bom = job._create_bom_for_job(product)

            # Crear MO con la BoM del job
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
            mo = job.env['mrp.production'].create(mo_vals)

            # Confirmar y planificar (genera WOs desde la BoM)
            if hasattr(mo, 'action_confirm'):
                mo.action_confirm()
            # El botón Plan planifica WOs según calendario de Work Centers (y dependencias si activas)
            if hasattr(mo, 'button_plan'):
                mo.button_plan()

            # Ajustar duración esperada en WOs según horas calculadas del job (en minutos)
            hours_map = job._compute_expected_hours()
            for wo in mo.workorder_ids:
                # Buscar por nombre de operación
                h = hours_map.get(wo.name)
                if h and h > 0:
                    # duration_expected está en MINUTOS
                    wo.write({'duration_expected': int(round(h * 60))})

            # Enlazar MO y notificar
            job.write({'production_id': mo.id})
            job.message_post(body=_('Se creó y planificó la Orden de Fabricación %s con Work Orders.') % (mo.name,))
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
            'target': 'current',
        }


