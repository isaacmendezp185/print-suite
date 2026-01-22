
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PrintJob(models.Model):
    _name = 'print.job'
    _description = 'Trabajo de impresión'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # Identificación
    name = fields.Char('Folio', default='Nuevo', copy=False, index=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', tracking=True)
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company, index=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='company_id.currency_id', store=True, readonly=True)

    # Parámetros técnicos de impresión
    substrate_id = fields.Many2one('print.substrate', string='Sustrato', tracking=True)
    ink_id = fields.Many2one('print.ink', string='Tinta', tracking=True)
    machine_id = fields.Many2one('print.machine', string='Máquina', tracking=True)
    workcenter_id = fields.Many2one('mrp.workcenter', string='Centro de trabajo',
                                    compute='_compute_workcenter', store=True, readonly=False)
    center_type = fields.Selection(related='machine_id.center_type', string='Tipo de centro', store=True, readonly=True)

    print_technology = fields.Selection([
        ('uv', 'UV'),
        ('latex', 'Látex'),
        ('eco', 'Ecosolvente'),
        ('sublimation', 'Sublimación'),
        ('aq', 'Base agua'),
    ], string='Tecnología de impresión', tracking=True)

    quality = fields.Selection([
        ('draft', 'Borrador'),
        ('standard', 'Estándar'),
        ('high', 'Alta'),
    ], string='Calidad', default='standard', tracking=True)

    # Dimensiones y cantidades
    width_mm = fields.Float('Ancho (mm)', tracking=True)
    height_mm = fields.Float('Alto (mm)', tracking=True)
    quantity = fields.Integer('Cantidad', default=1, tracking=True)
    area_m2 = fields.Float('Área total (m²)', compute='_compute_area', store=True)

    # Fechas y prioridad
    deadline_date = fields.Datetime('Fecha requerida')
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Alta'),
        ('2', 'Urgente'),
    ], string='Prioridad', default='0', tracking=True)

    # Costeo preliminar (a ser completado por print_costing_engine)
    cost_material = fields.Monetary('Costo material', currency_field='currency_id', tracking=True)
    cost_ink = fields.Monetary('Costo tinta', currency_field='currency_id', tracking=True)
    cost_machine = fields.Monetary('Costo máquina', currency_field='currency_id', tracking=True)
    cost_finishing = fields.Monetary('Costo acabados', currency_field='currency_id', tracking=True)
    cost_total = fields.Monetary('Costo total', currency_field='currency_id', tracking=True)

    # Producto para crear MO (opcional)
    product_id = fields.Many2one('product.product', string='Producto a fabricar/servicio')
    product_uom_id = fields.Many2one('uom.uom', string='UdM', default=lambda self: self.env.ref('uom.product_uom_unit'))
    product_qty = fields.Float('Cantidad a producir', default=1.0)

    # Estado
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('quoted', 'Cotizado'),
        ('approved', 'Aprobado'),
        ('in_production', 'En producción'),
        ('done', 'Terminado'),
        ('cancel', 'Cancelado'),
    ], string='Estado', default='draft', tracking=True)

    note = fields.Html('Notas internas')

    # Secuencia
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('print.job') or 'JOB-00000'
        recs = super().create(vals_list)
        return recs

    # Cálculos
    @api.depends('width_mm', 'height_mm', 'quantity')
    def _compute_area(self):
        for rec in self:
            w = (rec.width_mm or 0.0) / 1000.0
            h = (rec.height_mm or 0.0) / 1000.0
            qty = rec.quantity or 0
            rec.area_m2 = w * h * qty if w > 0 and h > 0 and qty > 0 else 0.0

    @api.depends('machine_id', 'machine_id.workcenter_id')
    def _compute_workcenter(self):
        for rec in self:
            rec.workcenter_id = rec.machine_id.workcenter_id if rec.machine_id and rec.machine_id.workcenter_id else rec.workcenter_id

    # Validaciones suaves
    @api.constrains('width_mm', 'height_mm', 'quantity')
    def _check_dimensions_qty(self):
        for rec in self:
            if rec.width_mm < 0 or rec.height_mm < 0:
                raise UserError(_('Las dimensiones no pueden ser negativas.'))
            if rec.quantity <= 0:
                raise UserError(_('La cantidad debe ser mayor a 0.'))

    # Flujo
    def action_set_quoted(self):
        self.filtered(lambda r: r.state == 'draft').write({'state': 'quoted'})

    def action_approve(self):
        self.filtered(lambda r: r.state in ('draft', 'quoted')).write({'state': 'approved'})

    def action_start_production(self):
        self.filtered(lambda r: r.state in ('approved', 'quoted')).write({'state': 'in_production'})

    def action_done(self):
        self.filtered(lambda r: r.state == 'in_production').write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    # Creación opcional de Orden de Fabricación (MRP)
    def action_create_mo(self):
        for rec in self:
            if not rec.product_id or rec.product_qty <= 0:
                raise UserError(_('Debes indicar un Producto y una Cantidad a producir para crear la Orden de Fabricación.'))
            mo_vals = {
                'product_id': rec.product_id.id,
                'product_qty': rec.product_qty,
                'product_uom_id': rec.product_uom_id.id or rec.product_id.uom_id.id,
                'origin': rec.name,
                'company_id': rec.company_id.id,
                'date_deadline': rec.deadline_date,
                # Nota: las operaciones por centro de trabajo vendrán de la BoM si existe.
            }
            mo = self.env['mrp.production'].create(mo_vals)
            # Enlazar chatter
            rec.message_post(body=_('Se creó la Orden de Fabricación <a href="#" data-oe-model="mrp.production" data-oe-id="%s">%s</a>.') % (mo.id, mo.name))
        return True
