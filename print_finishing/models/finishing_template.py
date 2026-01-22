from odoo import api, fields, models

class PrintFinishingTemplate(models.Model):
    _name = 'print.finishing.template'
    _description = 'Plantilla de acabados'
    _order = 'name'

    name = fields.Char('Nombre de plantilla', required=True)
    note = fields.Text('Notas')
    line_ids = fields.One2many('print.finishing.template.line', 'template_id', string='Líneas')

class PrintFinishingTemplateLine(models.Model):
    _name = 'print.finishing.template.line'
    _description = 'Línea de plantilla de acabado'
    _order = 'sequence, id'

    template_id = fields.Many2one('print.finishing.template', string='Plantilla', required=True, ondelete='cascade')

    sequence = fields.Integer('Secuencia', default=10)

    operation = fields.Selection([
        ('laminate', 'Laminado'),
        ('cut', 'Corte'),
        ('sew', 'Costura'),
        ('grommets', 'Ojillos'),
        ('pack', 'Empaque'),
        ('other', 'Otro'),
    ], string='Operación', required=True, default='laminate')

    basis = fields.Selection([
        ('area', 'Por área (m²)'),
        ('linear', 'Por lineal (m)'),
        ('time', 'Por tiempo (h)'),
        ('fixed', 'Costo fijo'),
    ], string='Base de cálculo', required=True, default='area')

    # Origen/cálculo de cantidad según base
    qty_mode = fields.Selection([
        ('job_area', 'Usar área del trabajo'),
        ('fixed_area', 'Área fija (m²)'),
        ('fixed_linear', 'Lineal fijo (m)'),
        ('none', 'No aplica'),
    ], string='Origen de cantidad', required=True, default='job_area',
       help='job_area: usa area_m2 del print.job; fixed_*: usa qty_value; none: no aplica a la base seleccionada.')

    qty_value = fields.Float('Cantidad fija', help='m² si fixed_area / m si fixed_linear')

    # Máquina sugerida (opcional). Si se deja vacía, el usuario la elige luego.
    machine_id = fields.Many2one('print.machine', string='Máquina sugerida')

    # Overrides por línea (opcionales)
    default_hours = fields.Float('Horas (si base tiempo)')
    default_fixed_cost = fields.Monetary('Costo fijo (si base fijo)', currency_field='currency_id')
    cost_hour_override = fields.Monetary('Costo/h (override línea)', currency_field='currency_id',
                                         help='Si > 0, se copia en la línea creada.')

    currency_id = fields.Many2one(
        'res.currency', string='Moneda',
        default=lambda self: self.env.company.currency_id.id, readonly=True
    )
