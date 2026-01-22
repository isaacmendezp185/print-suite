
from odoo import api, fields, models, _

class PrintJobFinishing(models.Model):
    _name = 'print.job.finishing'
    _description = 'Línea de acabado para trabajo de impresión'
    _order = 'sequence, id'

    sequence = fields.Integer('Secuencia', default=10)
    job_id = fields.Many2one('print.job', string='Trabajo', required=True, ondelete='cascade', index=True)

    name = fields.Char('Descripción', help='Texto libre para identificar la línea (opcional).')

    operation = fields.Selection([
        ('laminate', 'Laminado'),
        ('cut', 'Corte'),
        ('sew', 'Costura'),
        ('grommets', 'Ojillos'),
        ('pack', 'Empaque'),
        ('other', 'Otro'),
    ], string='Operación', required=True, default='laminate')

    # Tipo de centro sugerido según operación
    center_type = fields.Selection([
        ('large_format', 'Gran Formato'),
        ('rigid', 'Rígidos'),
        ('cutting', 'Corte'),
        ('packing_finishing', 'Empaque y acabados'),
    ], string='Tipo de centro', compute='_compute_center_type', store=True)

    machine_id = fields.Many2one(
        'print.machine', string='Máquina',
        domain="[('center_type','=',center_type), ('active','=',True)]"
    )
    workcenter_id = fields.Many2one(
        'mrp.workcenter', string='Centro de trabajo',
        compute='_compute_workcenter', store=True, readonly=False
    )

    # Bases de cálculo
    basis = fields.Selection([
        ('area', 'Por área (m²)'),
        ('linear', 'Por lineal (m)'),
        ('time', 'Por tiempo (h)'),
        ('fixed', 'Costo fijo'),
    ], string='Base de cálculo', required=True, default='area')

    quantity_area_m2 = fields.Float('Cantidad (m²)')
    quantity_linear_m = fields.Float('Cantidad (m)')
    hours = fields.Float('Horas (estimadas)', help='Se calcula por velocidad si aplica; editable.')
    fixed_cost = fields.Monetary('Costo fijo', currency_field='currency_id')

    # Costeo
    cost_hour_override = fields.Monetary('Costo/h (línea)', currency_field='currency_id',
                                         help='Si se deja 0, se toma costo/h de máquina o del centro.')
    currency_id = fields.Many2one(
        'res.currency', string='Moneda',
        related='job_id.company_id.currency_id', store=True, readonly=True
    )

    effective_cost_hour = fields.Monetary('Costo/h efectivo', currency_field='currency_id',
        compute='_compute_effective_cost_hour', store=False)
    cost_line = fields.Monetary('Costo de línea', currency_field='currency_id',
        compute='_compute_cost_line', store=True)

    note = fields.Text('Notas')

    _sql_constraints = [
        ('qty_area_nonneg', 'CHECK(quantity_area_m2 >= 0)', 'La cantidad en m² debe ser no negativa.'),
        ('qty_lin_nonneg', 'CHECK(quantity_linear_m >= 0)', 'La cantidad en metros debe ser no negativa.'),
        ('hours_nonneg', 'CHECK(hours >= 0)', 'Las horas deben ser no negativas.'),
        ('fixed_nonneg', 'CHECK(fixed_cost >= 0)', 'El costo fijo debe ser no negativo.'),
        ('override_nonneg', 'CHECK(cost_hour_override >= 0)', 'El costo/h debe ser no negativo.'),
    ]

    @api.depends('operation')
    def _compute_center_type(self):
        mapping = {
            'laminate': 'packing_finishing',
            'cut': 'cutting',
            'sew': 'packing_finishing',
            'grommets': 'packing_finishing',
            'pack': 'packing_finishing',
            'other': False,
        }
        for rec in self:
            rec.center_type = mapping.get(rec.operation)

    @api.depends('machine_id')
    def _compute_workcenter(self):
        for rec in self:
            rec.workcenter_id = rec.machine_id.workcenter_id if rec.machine_id else rec.workcenter_id

    @api.depends('cost_hour_override', 'machine_id.cost_hour_override', 'workcenter_id.costs_hour')
    def _compute_effective_cost_hour(self):
        for rec in self:
            rec.effective_cost_hour = (
                rec.cost_hour_override or
                rec.machine_id.cost_hour_override or
                rec.workcenter_id.costs_hour or
                0.0
            )

    @api.onchange('basis', 'quantity_area_m2', 'quantity_linear_m', 'machine_id')
    def _onchange_recompute_hours(self):
        for rec in self:
            h = rec.hours
            if rec.basis == 'area':
                speed = rec.machine_id.speed_m2_h or 0.0
                h = (rec.quantity_area_m2 / speed) if (rec.quantity_area_m2 and speed > 0) else 0.0
            elif rec.basis == 'linear':
                speed = rec.machine_id.speed_linear_m_h or 0.0
                h = (rec.quantity_linear_m / speed) if (rec.quantity_linear_m and speed > 0) else 0.0
            elif rec.basis == 'time':
                # el usuario define 'hours' manualmente
                h = rec.hours or 0.0
            elif rec.basis == 'fixed':
                h = 0.0
            rec.hours = h

    @api.depends('basis', 'hours', 'fixed_cost', 'effective_cost_hour')
    def _compute_cost_line(self):
        for rec in self:
            if rec.basis == 'fixed':
                rec.cost_line = rec.fixed_cost or 0.0
            else:
                rec.cost_line = (rec.hours or 0.0) * (rec.effective_cost_hour or 0.0)
