
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
