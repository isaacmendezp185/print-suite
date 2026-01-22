
from odoo import api, fields, models, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    print_job_count = fields.Integer(
        string='Trabajos de impresión',
        compute='_compute_print_job_count',
        store=False
    )

    def _compute_print_job_count(self):
        Job = self.env['print.job']
        for order in self:
            order.print_job_count = Job.search_count([('sale_line_id.order_id', '=', order.id)])

    def action_view_print_jobs(self):
        """Abre los print.job relacionados con este pedido/esta cotización."""
        self.ensure_one()
        action = self.env.ref('print_job_manager.action_print_job').read()[0]
        # Restringimos a los jobs ligados a este pedido
        action['domain'] = [('sale_line_id.order_id', '=', self.id)]
        # Contexto útil si creas nuevos desde la vista
        action['context'] = {
            'default_partner_id': self.partner_id.id,
        }
        return action
