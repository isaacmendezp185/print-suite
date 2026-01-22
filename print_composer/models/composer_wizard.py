

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PrintComposerWizard(models.TransientModel):
    _name = 'print.composer.wizard'
    _description = 'Asistente de composición de trabajos de impresión'

    # Contexto / empresa / moneda
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, readonly=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', store=True, readonly=True)

    # Cliente y fechas
    partner_id = fields.Many2one('res.partner', string='Cliente')
    deadline_date = fields.Datetime('Fecha requerida')
    priority = fields.Selection([
        ('0', 'Normal'), ('1', 'Alta'), ('2', 'Urgente'),
    ], default='0', string='Prioridad')

    # Tipo de centro (para filtrar/pre-cargar máquina)
    center_type = fields.Selection([
        ('large_format', 'Gran Formato'),
        ('rigid', 'Rígidos'),
        ('cutting', 'Corte'),
        ('packing_finishing', 'Empaque y acabados'),
    ], string='Tipo de centro')

    # Materiales
    substrate_id = fields.Many2one('print.substrate', string='Sustrato', required=True)
    ink_id = fields.Many2one('print.ink', string='Tinta')

    # Máquina / Centro
    machine_id = fields.Many2one('print.machine', string='Máquina', required=True,
                                 domain="[('center_type','=',center_type)]")
    workcenter_id = fields.Many2one('mrp.workcenter', string='Centro de trabajo',
                                    compute='_compute_workcenter', store=False, readonly=True)

    # Parámetros de impresión
    print_technology = fields.Selection([
        ('uv', 'UV'), ('latex', 'Látex'), ('eco', 'Ecosolvente'),
        ('sublimation', 'Sublimación'), ('aq', 'Base agua'),
    ], string='Tecnología')
    quality = fields.Selection([
        ('draft', 'Borrador'), ('standard', 'Estándar'), ('high', 'Alta'),
    ], default='standard', string='Calidad')

    # Medidas / cantidad
    width_mm = fields.Float('Ancho (mm)', required=True)
    height_mm = fields.Float('Alto (mm)', required=True)
    quantity = fields.Integer('Cantidad', required=True, default=1)
    area_m2 = fields.Float('Área total (m²)', compute='_compute_area', store=False)

    # MO opcional
    create_mo = fields.Boolean('Crear Orden de Fabricación')
    product_id = fields.Many2one('product.product', string='Producto a fabricar/servicio')
    product_uom_id = fields.Many2one('uom.uom', string='UdM', default=lambda s: s.env.ref('uom.product_uom_unit'))
    product_qty = fields.Float('Cantidad a producir', default=1.0)

    # Costeo opcional
    estimate_costs = fields.Boolean('Estimar costos')

    # Enlace (si viene de línea de venta)
    sale_line_id = fields.Many2one('sale.order.line', string='Línea de venta')

    note = fields.Html('Notas')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Soportar defaults desde línea de venta (context)
        ctx = self.env.context
        if ctx.get('default_partner_id'):
            res['partner_id'] = ctx['default_partner_id']
        if ctx.get('default_product_id'):
            res['product_id'] = ctx['default_product_id']
        if ctx.get('default_product_uom_id'):
            res['product_uom_id'] = ctx['default_product_uom_id']
        if ctx.get('default_product_qty'):
            res['product_qty'] = ctx['default_product_qty']
        if ctx.get('default_sale_line_id'):
            res['sale_line_id'] = ctx['default_sale_line_id']
        if 'default_create_mo' in ctx:
            res['create_mo'] = bool(ctx['default_create_mo'])
        if 'default_estimate_costs' in ctx:
            res['estimate_costs'] = bool(ctx['default_estimate_costs'])
        return res

    @api.depends('machine_id')
    def _compute_workcenter(self):
        for w in self:
            w.workcenter_id = w.machine_id.workcenter_id if w.machine_id else False

    @api.depends('width_mm', 'height_mm', 'quantity')
    def _compute_area(self):
        for w in self:
            w.area_m2 = ((w.width_mm or 0.0) / 1000.0) * ((w.height_mm or 0.0) / 1000.0) * (w.quantity or 0)

    def _validate_inputs(self):
        for w in self:
            if w.width_mm <= 0 or w.height_mm <= 0:
                raise UserError(_('Las dimensiones deben ser mayores a 0.'))
            if w.quantity <= 0:
                raise UserError(_('La cantidad debe ser mayor a 0.'))
            if w.create_mo and (not w.product_id or w.product_qty <= 0):
                raise UserError(_('Para crear la MO debes indicar Producto y Cantidad a producir.'))

    @api.onchange('center_type')
    def _onchange_center_type(self):
        """ Pre-selecciona la primera máquina del tipo elegido. """
        for w in self:
            if w.center_type:
                m = self.env['print.machine'].search([('center_type', '=', w.center_type), ('active', '=', True)], limit=1)
                w.machine_id = m.id if m else False
            else:
                w.machine_id = False

    @api.onchange('substrate_id')
    def _onchange_substrate(self):
        """ Aplica reglas sugeridas del sustrato: tinta y calidad. """
        for w in self:
            if not w.substrate_id:
                continue
            sub = w.substrate_id
            # Tinta sugerida
            if sub.default_ink_id:
                w.ink_id = sub.default_ink_id.id
                # Alinear tecnología con la tinta sugerida
                if sub.default_ink_id.technology:
                    w.print_technology = sub.default_ink_id.technology
            # Calidad sugerida
            if sub.default_quality:
                w.quality = sub.default_quality

    def action_confirm(self):
        """Crea print.job, opcionalmente estima costos y crea MO. Devuelve acción para abrir el job."""
        self._validate_inputs()
        self.ensure_one()
        vals = {
            'partner_id': self.partner_id.id if self.partner_id else False,
            'company_id': self.company_id.id,
            'substrate_id': self.substrate_id.id,
            'ink_id': self.ink_id.id if self.ink_id else False,
            'machine_id': self.machine_id.id,
            'workcenter_id': self.workcenter_id.id if self.workcenter_id else False,
            'print_technology': self.print_technology or False,
            'quality': self.quality,
            'width_mm': self.width_mm,
            'height_mm': self.height_mm,
            'quantity': self.quantity,
            'deadline_date': self.deadline_date,
            'priority': self.priority,
            'note': self.note,
            # Producto/MRP opcional
            'product_id': self.product_id.id if self.product_id else False,
            'product_uom_id': self.product_uom_id.id if self.product_uom_id else False,
            'product_qty': self.product_qty if self.product_id else 0.0,
            # Enlace con la línea de venta
            'sale_line_id': self.sale_line_id.id if self.sale_line_id else False,
        }
        job = self.env['print.job'].create(vals)

        # Estimar costos (si se marcó)
        if self.estimate_costs:
            job.action_estimate_costs()

        # Crear MO (si se marcó)
        if self.create_mo:
            job.action_create_mo()

        # Abrir el trabajo creado
        return {
            'type': 'ir.actions.act_window',
            'name': _('Trabajo creado'),
            'res_model': 'print.job',
            'res_id': job.id,
            'view_mode': 'form',
            'target': 'current',
        }
