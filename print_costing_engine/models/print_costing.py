
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PrintJob(models.Model):
    _inherit = 'print.job'

    def action_estimate_costs(self):
        """
        Calcula y escribe:
          - cost_material
          - cost_ink
          - cost_machine
          - cost_finishing (queda como esté; 0 si no hay módulo de acabados)
          - cost_total = suma
        Reglas (resumen):
          * Material:
            - Flex: usa substrate.cost_m2; si 0, intenta derivar (ya lo tienes computado en print.substrate).
            - Rígido: usa substrate.cost_m2_sheet si aplica.
          * Tinta: ink.cost_ml * ink.consumption_ml_m2 * area_m2
          * Máquina: horas = area_m2 / speed_m2_h; costo/h = override o workcenter.costs_hour
        """
        for job in self:
            # Validaciones mínimas
            if not job.substrate_id:
                raise UserError(_("Debes seleccionar un Sustrato."))
            if not job.machine_id:
                raise UserError(_("Debes seleccionar una Máquina."))
            if job.area_m2 <= 0:
                raise UserError(_("El área total (m²) debe ser mayor a 0. Revisa ancho/alto/cantidad."))

            # ---------- Material ----------
            cost_material = 0.0
            sub = job.substrate_id
            cost_m2_flex = sub.cost_m2 or 0.0
            cost_m2_rigid = sub.cost_m2_sheet or 0.0
            # si el tipo declara flex, prioriza cost_m2; si rigid, prioriza cost_m2_sheet
            if sub.substrate_kind == 'flex':
                base_cost_m2 = cost_m2_flex if cost_m2_flex > 0 else cost_m2_rigid
            else:
                base_cost_m2 = cost_m2_rigid if cost_m2_rigid > 0 else cost_m2_flex
            if base_cost_m2 > 0 and job.area_m2 > 0:
                cost_material = base_cost_m2 * job.area_m2

            # ---------- Tinta ----------
            cost_ink = 0.0
            if job.ink_id:
                ink = job.ink_id
                # Factor opcional por calidad (puedes ajustar si lo deseas)
                # draft: -10% consumo; high: +10% consumo (ejemplo simple)
                quality_factor = {
                    'draft': 0.9,
                    'standard': 1.0,
                    'high': 1.1,
                }.get(job.quality or 'standard', 1.0)
                cost_ink_per_m2 = (ink.cost_ml or 0.0) * (ink.consumption_ml_m2 or 0.0) * quality_factor
                cost_ink = cost_ink_per_m2 * job.area_m2

            # ---------- Máquina ----------
            cost_machine = 0.0
            m = job.machine_id
            # Costo/h efectivo (módulo 2 ya lo mostraba como campo compute, replicamos la lógica)
            effective_cost_hour = (m.cost_hour_override or 0.0) or (m.workcenter_id.costs_hour or 0.0)
            hours_machine = 0.0
            if (m.speed_m2_h or 0.0) > 0:
                # Si la calidad es alta, asumimos -10% de velocidad efectiva (opcional)
                speed_factor = {
                    'draft': 1.05,     # un poco más rápido
                    'standard': 1.0,
                    'high': 0.9,       # un poco más lento por mayor pasadas
                }.get(job.quality or 'standard', 1.0)
                eff_speed_m2_h = (m.speed_m2_h or 0.0) * speed_factor
                if eff_speed_m2_h > 0:
                    hours_machine = job.area_m2 / eff_speed_m2_h

            # Si en el futuro usas procesos estrictamente lineales, calcularías:
            # if (m.speed_linear_m_h or 0.0) > 0 and job.linear_m > 0:
            #     hours_machine = job.linear_m / m.speed_linear_m_h
            # Por ahora, nos quedamos con m².

            if hours_machine > 0 and effective_cost_hour > 0:
                cost_machine = hours_machine * effective_cost_hour

            # ---------- Acabados ----------
            # En este módulo no gestionamos líneas de acabados; respetamos lo que esté en el campo.
            cost_finishing = job.cost_finishing or 0.0

            # ---------- Total ----------
            job.write({
                'cost_material': cost_material,
                'cost_ink': cost_ink,
                'cost_machine': cost_machine,
                'cost_total': (cost_material or 0.0) + (cost_ink or 0.0) + (cost_machine or 0.0) + (cost_finishing or 0.0),
            })

            # Notificación en chatter
            job.message_post(
                body=_(
                    "Costeo estimado actualizado:<br/>"
                    "- Material: %(cm).2f<br/>"
                    "- Tinta: %(ci).2f<br/>"
                    "- Máquina: %(cma).2f<br/>"
                    "- Acabados: %(cf).2f<br/>"
                    "<b>Total:</b> %(ct).2f"
                ) % {
                    'cm': job.cost_material,
                    'ci': job.cost_ink,
                    'cma': job.cost_machine,
                    'cf': job.cost_finishing or 0.0,
                    'ct': job.cost_total,
                }
            )
        return True
