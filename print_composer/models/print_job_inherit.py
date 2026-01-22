
# print_composer/models/print_job_inherit.py
from odoo import fields, models

class PrintJob(models.Model):
    _inherit = 'print.job'

    sale_line_id = fields.Many2one('sale.order.line', string='Línea de venta', index=True)
