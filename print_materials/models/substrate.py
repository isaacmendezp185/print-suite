
from odoo import api, fields, models

class PrintSubstrate(models.Model):
    _name = 'print.substrate'
    _description = 'Sustrato (material de impresión)'
    _order = 'name'

    name = fields.Char('Nombre', required=True)
    code = fields.Char('Código', index=True)
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company, index=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='company_id.currency_id', store=True, readonly=True)

    # Parámetros de rollo (para materiales flexibles)
    width_usable_mm = fields.Float('Ancho útil (mm)', help='Ancho utilizable del rollo en milímetros')
    length_roll_m = fields.Float('Largo del rollo (m)')
    area_roll_m2 = fields.Float('Área por rollo (m²)', compute='_compute_area_roll_m2', store=True)
    waste_rate = fields.Float('Merma (%)', help='Porcentaje de merma estimada (0-100)')

    # Costos
    cost_roll = fields.Monetary('Costo por rollo', currency_field='currency_id')
    cost_m2 = fields.Monetary('Costo por m² (estimado)', currency_field='currency_id', compute='_compute_cost_m2', store=True)

    # Clasificación
    substrate_kind = fields.Selection([
        ('flex', 'Flexible (lona, vinil, mesh, tela)'),
        ('rigid', 'Rígido (acrílico, PVC, foamboard)'),
    ], string='Tipo de sustrato', default='flex', required=True)

    # Para rígidos por hoja (opcional)
    sheet_width_mm = fields.Float('Ancho hoja (mm)')
    sheet_height_mm = fields.Float('Alto hoja (mm)')
    sheet_area_m2 = fields.Float('Área por hoja (m²)', compute='_compute_sheet_area', store=True)
    cost_sheet = fields.Monetary('Costo por hoja', currency_field='currency_id')
    cost_m2_sheet = fields.Monetary('Costo por m² de hoja', currency_field='currency_id', compute='_compute_cost_m2_sheet', store=True)

    description = fields.Text('Descripción')

    _sql_constraints = [
        ('width_positive', 'CHECK(width_usable_mm >= 0)', 'El ancho útil debe ser no negativo.'),
        ('length_positive', 'CHECK(length_roll_m >= 0)', 'El largo de rollo debe ser no negativo.'),
        ('waste_range', 'CHECK(waste_rate >= 0 AND waste_rate <= 100)', 'La merma debe estar entre 0 y 100%.'),
        ('sheet_dims', 'CHECK(sheet_width_mm >= 0 AND sheet_height_mm >= 0)', 'Dimensiones de hoja no válidas.'),
    ]

    @api.depends('width_usable_mm', 'length_roll_m')
    def _compute_area_roll_m2(self):
        for rec in self:
            w_m = (rec.width_usable_mm or 0.0) / 1000.0
            rec.area_roll_m2 = (w_m * (rec.length_roll_m or 0.0)) if (w_m > 0 and rec.length_roll_m > 0) else 0.0

    @api.depends('cost_roll', 'area_roll_m2', 'waste_rate')
    def _compute_cost_m2(self):
        for rec in self:
            if rec.area_roll_m2 > 0:
                factor_merma = 1.0 + (rec.waste_rate or 0.0) / 100.0
                rec.cost_m2 = (rec.cost_roll or 0.0) / rec.area_roll_m2 * factor_merma
            else:
                rec.cost_m2 = 0.0

    @api.depends('sheet_width_mm', 'sheet_height_mm')
    def _compute_sheet_area(self):
        for rec in self:
            rec.sheet_area_m2 = (rec.sheet_width_mm or 0.0) * (rec.sheet_height_mm or 0.0) / 1_000_000.0

    @api.depends('cost_sheet', 'sheet_area_m2', 'waste_rate')
    def _compute_cost_m2_sheet(self):
        for rec in self:
            if rec.sheet_area_m2 > 0:
                factor_merma = 1.0 + (rec.waste_rate or 0.0) / 100.0
                rec.cost_m2_sheet = (rec.cost_sheet or 0.0) / rec.sheet_area_m2 * factor_merma
            else:
                rec.cost_m2_sheet = 0.0
