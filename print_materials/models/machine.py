
from odoo import api, fields, models

class PrintMachine(models.Model):
    _name = 'print.machine'
    _description = 'Máquina de impresión / corte / laminado'
    _order = 'name'

    name = fields.Char('Nombre de máquina', required=True)
    code = fields.Char('Código', index=True)
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company, index=True)

    # Vinculación a Centro de trabajo MRP
    workcenter_id = fields.Many2one('mrp.workcenter', string='Centro de trabajo', required=True, index=True)

    # Afinidad con los 4 tipos (coincide con mrp.workcenter.print_center_type)
    center_type = fields.Selection([
        ('large_format', 'Gran Formato'),
        ('rigid', 'Rígidos'),
        ('cutting', 'Corte'),
        ('packing_finishing', 'Empaque y acabados'),
    ], string='Tipo de centro', required=True)

    # Clasificación funcional
    machine_role = fields.Selection([
        ('printer', 'Impresora'),
        ('cutter', 'Cortadora'),
        ('laminator', 'Laminadora'),
        ('sewing', 'Costura'),
        ('packing', 'Empaque'),
        ('other', 'Otro'),
    ], string='Función', required=True, default='printer')

    # Rendimientos
    speed_m2_h = fields.Float('Velocidad (m²/h)', help='Para procesos por superficie: impresión, laminado.')
    speed_linear_m_h = fields.Float('Velocidad lineal (m/h)', help='Para procesos lineales: corte, costura.')
    # Costeo
    cost_hour_override = fields.Monetary('Costo/h (máquina)', currency_field='currency_id',
                                         help='Si se deja vacío o 0, se usará el costo/h del Centro de trabajo.')
    currency_id = fields.Many2one('res.currency', string='Moneda',
                                  related='company_id.currency_id', store=True, readonly=True)

    effective_cost_hour = fields.Monetary('Costo/h efectivo', currency_field='currency_id',
                                          compute='_compute_effective_cost', store=False)

    supported_inks = fields.Many2many('print.ink', 'print_machine_ink_rel', 'machine_id', 'ink_id', string='Tintas soportadas')
    active = fields.Boolean('Activo', default=True)
    note = fields.Text('Notas')

    _sql_constraints = [
        ('speed_m2_nonneg', 'CHECK(speed_m2_h >= 0)', 'La velocidad m²/h debe ser no negativa.'),
        ('speed_lin_nonneg', 'CHECK(speed_linear_m_h >= 0)', 'La velocidad m/h debe ser no negativa.'),
        ('cost_nonneg', 'CHECK(cost_hour_override >= 0)', 'El costo/h debe ser no negativo.'),
    ]

    @api.depends('cost_hour_override', 'workcenter_id.costs_hour')
    def _compute_effective_cost(self):
        for rec in self:
            rec.effective_cost_hour = rec.cost_hour_override or rec.workcenter_id.costs_hour or 0.0

    @api.onchange('workcenter_id')
    def _onchange_workcenter(self):
        """Si el centro tiene tipo, proponlo como center_type."""
        for rec in self:
            if rec.workcenter_id and rec.workcenter_id.print_center_type:
                rec.center_type = rec.workcenter_id.print_center_type
