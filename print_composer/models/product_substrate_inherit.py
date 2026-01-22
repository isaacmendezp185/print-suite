
from odoo import fields, models

class PrintSubstrate(models.Model):
    _inherit = 'print.substrate'

    use_case = fields.Selection([
        ('exterior', 'Exterior'),
        ('interior', 'Interior'),
        ('backlit', 'Backlit (retroiluminado)'),
        ('vehicular', 'Vehicular / wrap'),
        ('floor', 'Piso'),
        ('other', 'Otro'),
    ], string='Uso sugerido')

    default_ink_id = fields.Many2one('print.ink', string='Tinta sugerida')
    default_quality = fields.Selection([
        ('draft', 'Borrador'),
        ('standard', 'Estándar'),
        ('high', 'Alta'),
    ], string='Calidad sugerida', default=False)
