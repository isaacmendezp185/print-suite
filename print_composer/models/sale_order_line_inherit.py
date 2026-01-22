
from odoo import api, models, _

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def action_open_print_composer(self):
        self.ensure_one()
        order = self.order_id
        ctx = {
            'default_partner_id': order.partner_id.id if order.partner_id else False,
            'default_product_id': self.product_id.id or False,
            'default_product_uom_id': self.product_uom.id or False,
            'default_product_qty': self.product_uom_qty or 1.0,
            # sugerencias del flujo
            'default_create_mo': True,
            'default_estimate_costs': True,
            # enlace de vuelta a la línea
            'default_sale_line_id': self.id,
        }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Asistente de composición'),
            'res_model': 'print.composer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': ctx,
        }
