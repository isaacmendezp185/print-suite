
from odoo import fields, models

class PrintInk(models.Model):
    _name = 'print.ink'
    _description = 'Tinta de impresión'
    _order = 'name'

    name = fields.Char('Nombre', required=True)
    code = fields.Char('Código', index=True)
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company, index=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='company_id.currency_id', store=True, readonly=True)

    technology = fields.Selection([
        ('uv', 'UV'),
        ('latex', 'Látex'),
        ('eco', 'Ecosolvente'),
        ('sublimation', 'Sublimación'),
        ('aq', 'Base agua'),
    ], string='Tecnología', required=True, default='uv')

    color = fields.Char('Color / Set', help='Color específico o set (CMYK, CMYK+W, etc.)')

    cost_ml = fields.Monetary('Costo por ml', currency_field='currency_id')
    consumption_ml_m2 = fields.Float('Consumo (ml/m²)', help='Consumo estimado para costeo por superficie')
    note = fields.Text('Notas')

    _sql_constraints = [
        ('cost_ml_nonneg', 'CHECK(cost_ml >= 0)', 'El costo por ml debe ser no negativo.'),
        ('consumption_nonneg', 'CHECK(consumption_ml_m2 >= 0)', 'El consumo debe ser no negativo.'),
    ]
