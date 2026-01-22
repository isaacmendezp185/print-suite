from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PrintFinishingApplyTemplateWizard(models.TransientModel):
    _name = 'print.finishing.apply.template.wizard'
    _description = 'Aplicar plantilla de acabados a un trabajo'

    job_id = fields.Many2one('print.job', string='Trabajo', readonly=True)
    template_id = fields.Many2one('print.finishing.template', string='Plantilla', required=True)
    clear_existing = fields.Boolean('Borrar líneas existentes', default=False)
    estimate_after = fields.Boolean('Estimar costos al finalizar', default=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx = self.env.context
        if ctx.get('active_model') == 'print.job' and ctx.get('active_id'):
            res['job_id'] = ctx['active_id']
        return res

    def action_apply(self):
        self.ensure_one()
        job = self.job_id
        if not job:
            raise UserError(_('Este asistente debe abrirse desde un Trabajo de impresión.'))
        if not self.template_id.line_ids:
            raise UserError(_('La plantilla seleccionada no tiene líneas.'))

        # Limpieza previa
        if self.clear_existing:
            job.finishing_line_ids.unlink()

        # Crear líneas a partir de la plantilla
        line_vals_list = []
        for tl in self.template_id.line_ids:
            vals = {
                'job_id': job.id,
                'sequence': tl.sequence,
                'operation': tl.operation,
                'basis': tl.basis,
                'machine_id': tl.machine_id.id or False,
            }
            # Copiar overrides
            if tl.cost_hour_override and tl.cost_hour_override > 0:
                vals['cost_hour_override'] = tl.cost_hour_override

            # Cantidades según base y modo
            if tl.basis == 'area':
                if tl.qty_mode == 'job_area':
                    vals['quantity_area_m2'] = job.area_m2 or 0.0
                elif tl.qty_mode == 'fixed_area':
                    vals['quantity_area_m2'] = tl.qty_value or 0.0
                else:
                    vals['quantity_area_m2'] = 0.0

            elif tl.basis == 'linear':
                if tl.qty_mode == 'fixed_linear':
                    vals['quantity_linear_m'] = tl.qty_value or 0.0
                else:
                    vals['quantity_linear_m'] = 0.0

            elif tl.basis == 'time':
                vals['hours'] = tl.default_hours or 0.0

            elif tl.basis == 'fixed':
                vals['fixed_cost'] = tl.default_fixed_cost or 0.0

            line_vals_list.append(vals)

        if line_vals_list:
            self.env['print.job.finishing'].create(line_vals_list)

        # Recalcular costos si procede
        if self.estimate_after:
            job.action_estimate_costs()

        # Volver al job
        return {
            'type': 'ir.actions.act_window',
            'name': _('Trabajo de impresión'),
            'res_model': 'print.job',
            'res_id': job.id,
            'view_mode': 'form',
            'target': 'current',
        }
