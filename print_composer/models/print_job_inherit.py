
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PrintJob(models.Model):
    _inherit = 'print.job'

    sale_line_id = fields.Many2one('sale.order.line', string='Línea de venta', index=True)

    def action_open_sale_order(self):
        """Abre la cotización/pedido de venta vinculado a este trabajo."""
        self.ensure_one()
        if not self.sale_line_id or not self.sale_line_id.order_id:
            raise UserError(_('Este trabajo no está vinculado a ninguna cotización/pedido.'))
        order = self.sale_line_id.order_id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pedido de venta'),
            'res_model': 'sale.order',
            'res_id': order.id,
            'view_mode': 'form',
            'target': 'current',
        }
