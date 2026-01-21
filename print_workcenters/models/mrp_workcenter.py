
from odoo import api, fields, models

class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    print_center_type = fields.Selection(
        selection=[
            ('rigid', 'Rígidos'),
            ('large_format', 'Gran Formato'),
            ('cutting', 'Corte'),
            ('packing_finishing', 'Empaque y acabados'),
        ],
        string='Tipo de centro de impresión',
        help='Clasificación del centro de trabajo usado en impresión gran formato.'
    )