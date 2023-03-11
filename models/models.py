# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError
from odoo import models, fields, api, _
import logging

logger = logging.getLogger(__name__)


class SaleOrderInherit(models.Model):
    _inherit = "sale.order"

    delivery_date = fields.Date("Date prévue de livraison", required=True)

    street = fields.Char("Rue", required=True)
    city = fields.Char("Cité", required=True,
                       compute="_compute_city", readonly=False, store=True)
    zip = fields.Char("ZIP", required=True,
                      compute="_compute_zip", readonly=False, store=True)
    state_id = fields.Many2one("res.country.state", "État")
    contact_name = fields.Char("Personne à contacter", required=True)
    phone = fields.Char("Téléphone", required=True)

    country_enforce_cities = fields.Boolean()

    def _default_partner(self):
        return self.env.user.partner_id.parent_id.id if self.env.user.partner_id.parent_id.id else self.env.user.partner_id.id

    partner_id = fields.Many2one(
        'res.partner', string='Client', default=_default_partner)

    zip_id = fields.Many2one(
        comodel_name="res.city.zip",
        string="ZIP Location",
        index=True,
        compute="_compute_zip_id",
        readonly=False,
        store=True,
    )
    city_id = fields.Many2one(
        "res.city",
        index=True,  # add index for performance
        compute="_compute_city_id",
        readonly=False,
        store=True,
    )
    country_id = fields.Many2one("res.country",
                                 compute="_compute_country_id", readonly=False, store=True
                                 )
    state_id = fields.Many2one("res.country.state",
                               compute="_compute_state_id", readonly=False, store=True)

    @api.depends("state_id", "country_id", "city_id", "zip")
    def _compute_zip_id(self):
        """Empty the zip auto-completion field if data mismatch when on UI."""
        for record in self.filtered("zip_id"):
            fields_map = {
                "zip": "name",
                "city_id": "city_id",
                "state_id": "state_id",
                "country_id": "country_id",
            }
            for rec_field, zip_field in fields_map.items():
                if (
                    record[rec_field]
                    and record[rec_field] != record._origin[rec_field]
                    and record[rec_field] != record.zip_id[zip_field]
                ):
                    record.zip_id = False
                    break

    @api.depends("zip_id")
    def _compute_city_id(self):
        if hasattr(super(), "_compute_city_id"):
            super()._compute_city_id()  # pragma: no cover
        for record in self:
            if record.zip_id:
                record.city_id = record.zip_id.city_id
            elif not record.country_enforce_cities:
                record.city_id = False

    @api.depends("zip_id")
    def _compute_city(self):
        if hasattr(super(), "_compute_city"):
            super()._compute_city()  # pragma: no cover
        for record in self:
            if record.zip_id:
                record.city = record.zip_id.city_id.name

    @api.depends("zip_id")
    def _compute_zip(self):
        if hasattr(super(), "_compute_zip"):
            super()._compute_zip()  # pragma: no cover
        for record in self:
            if record.zip_id:
                record.zip = record.zip_id.name

    @api.depends("zip_id", "state_id")
    def _compute_country_id(self):
        if hasattr(super(), "_compute_country_id"):
            super()._compute_country_id()  # pragma: no cover
        for record in self:
            if record.zip_id.city_id.country_id:
                record.country_id = record.zip_id.city_id.country_id
            elif record.state_id:
                record.country_id = record.state_id.country_id

    @api.depends("zip_id")
    def _compute_state_id(self):
        if hasattr(super(), "_compute_state_id"):
            super()._compute_state_id()  # pragma: no cover
        for record in self:
            state = record.zip_id.city_id.state_id
            if state and record.state_id != state:
                record.state_id = record.zip_id.city_id.state_id

    @api.constrains("zip_id", "country_id", "city_id", "state_id", "zip")
    def _check_zip(self):
        if self.env.context.get("skip_check_zip"):
            return
        for rec in self:
            if not rec.zip_id:
                continue
            if rec.zip_id.city_id.country_id != rec.country_id:
                raise ValidationError(
                    _("The country of the partner %s differs from that in location %s")
                    % (rec.name, rec.zip_id.name)
                )
            if rec.zip_id.city_id.state_id != rec.state_id:
                raise ValidationError(
                    _("The state of the partner %s differs from that in location %s")
                    % (rec.name, rec.zip_id.name)
                )
            if rec.zip_id.city_id != rec.city_id:
                raise ValidationError(
                    _("The city of partner %s differs from that in location %s")
                    % (rec.name, rec.zip_id.name)
                )
            if rec.zip_id.name != rec.zip:
                raise ValidationError(
                    _("The zip of the partner %s differs from that in location %s")
                    % (rec.name, rec.zip_id.name)
                )

    def _zip_id_domain(self):
        return """
            [
                ("city_id", "=?", city_id),
                ("city_id.country_id", "=?", country_id),
                ("city_id.state_id", "=?", state_id),
            ]
        """

    @api.model
    def _fields_view_get_address(self, arch):
        # We want to use a domain that requires city_id to be on the view
        # but we can't add it directly there, otherwise _fields_view_get_address
        # in base_address_city won't do its magic, as it immediately returns
        # if city_id is already in there. On the other hand, if city_id is not in the
        # views, odoo won't let us use it in zip_id's domain.
        # For this reason we need to set the domain here.
        arch = super()._fields_view_get_address(arch)
        doc = etree.fromstring(arch)
        for node in doc.xpath("//field[@name='zip_id']"):
            node.attrib["domain"] = self._zip_id_domain()
        return etree.tostring(doc, encoding="unicode")

    @api.model
    def _address_fields(self):
        return super()._address_fields() + ["zip_id"]

   # def action_confirm(self):
   #     super().action_confirm()

   #     # Send email to addmin
   #     self._send_quotation_email()

   #     return True

    # def action_cancel(self):
    #     result = super().action_cancel()
    #     self._send_quotation_cancel_email()
    #     return result

    # def _send_quotation_email(self):
    #     mail_template = self.env.ref('custom_sfcd.email_quotation_sent')
    #     mail_template.send_mail(self.id, force_send=True)

    # def _send_quotation_cancel_email(self):
    #     mail_template = self.env.ref('custom_sfcd.email_quotation_cancel')
    #     mail_template.send_mail(self.id, force_send=True)


class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    brand_id = fields.Many2one('product.brand',)

    quantity_in_stock = fields.Float(
        "Quantité en stock", readonly=True, store=False, compute="_compute_qty_in_stock")

    @api.depends('product_id')
    def _compute_qty_in_stock(self):
        for order_line in self:
            order_line.quantity_in_stock = order_line.product_id.qty_available

    @api.constrains("product_uom_qty")
    def _constrain_qty_valid(self):
        for order_line in self:
            if order_line.product_uom_qty > order_line.quantity_in_stock:
                raise ValidationError(
                    "Vous ne pouvez pas demander une quantité superieure à la quantité en stock")


class ResPartnerExtends(models.Model):
    _inherit = 'res.partner'

    email = fields.Char(string='Email', required=True)
    is_user_linked = fields.Boolean(default=False)

    def create_linked_user(self):
        partner_id = self.env.context.get('partner_id')
        params = self.env.context.get('params')

        partner = None
        if params and 'id' in params:
            active_id = int(params['id'])
            partner = self.env['res.partner'].browse(active_id)

        elif partner_id:
            partner = self.env['res.partner'].browse(partner_id)

        if partner is not None and self.env['res.users'].search_count([('login', '=', partner.email)]) == 0:
            # Load the default user template
            template = self.env.ref('base.default_user')

            # Create a new user from the template
            new_user = self.env['res.users'].create({
                'name': partner.name,
                'login': partner.email,
                'email': partner.email,
                'password': partner.email
            })

            new_user.partner_id.update({
                "is_user_linked": True,
                "parent_id": partner.parent_id,
                "type": partner.type,
                "street": partner.street,
                "street2": partner.street2,
                "city": partner.city,
                "state_id": partner.state_id,
                "zip": partner.zip,
                "country_id": partner.country_id,
                "vat": partner.vat,
                "function": partner.function,
                "phone": partner.phone,
                "mobile": partner.email,
                "website": partner.website,
                "title": partner.title,
                "category_id": partner.category_id
            })

            self.grant_permissions(template.id, new_user.id)

            partner.unlink()

            return {
                'name': 'Customers',
                'view_type': 'kanban',
                'view_mode': 'kanban,tree,form',
                'res_model': 'res.partner',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'domain': [('is_company', '=', True), ('customer_rank', '>', 0)]
            }

    @api.model
    def grant_permissions(self, user1_id, user2_id):
        user1 = self.env['res.users'].browse(user1_id)
        user2 = self.env['res.users'].browse(user2_id)

        # Get the groups of user1
        groups = user1.groups_id

        # Assign the same groups to user2
        user2.write({
            'groups_id': [(6, 0, groups.ids)],
            'hide_menu_access_ids': user1.hide_menu_access_ids
        })

    @api.model
    def create(self, vals):
        email = vals.get('email')

        ResUser = self.env['res.users']

        if ResUser.search_count([('login', '=', email)]) > 0:
            raise ValidationError(
                "Un utilisateur avec ce email existe déjà")

        result = super(ResPartnerExtends, self).create(vals)

        # Add a custom key and value to the context
        self.with_context({'partner_id': result.id})

        return result


class ProductTemplateInherit(models.Model):
    _inherit = "product.template"

    partner_id = fields.Many2one('res.partner', "Client", required=True)

    type = fields.Selection(default='product')

    longueur = fields.Float('Longueur', default=0.0)
    longueur_uom_name = fields.Char("cm", readonly=True, default="cm")

    largeur = fields.Float('Largeur', default=0.0)
    largeur_uom_name = fields.Char("cm", readonly=True, default="cm")

    hauteur = fields.Float('Hauteur', default=0.0)
    hauteur_uom_name = fields.Char("cm", readonly=True, default="cm")

    volume = fields.Float('Volume', compute='_compute_volume', store=True)

    @api.depends('longueur', 'largeur', 'hauteur')
    def _compute_volume(self):
        for record in self:
            record.volume = record.longueur*record.largeur*record.hauteur

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):

        # Get the connected user
        user = self.env.user

        domain = None

        if not self.env.is_admin():
            domain = [('partner_id.user_ids', 'like', user.id)]

        return super(ProductTemplateInherit, self).search_read(domain, fields, offset, limit, order)

    @api.model
    def _name_search(self, name, args=None, operator="ilike", limit=100, name_get_uid=None):
        args = args or []

        domain = []

        # Get the connected user
        user = self.env.user

        if not self.env.is_admin():
            domain = [('partner_id.user_ids', 'like', user.id)]

        return self._search(domain+args, limit=limit, access_rights_uid=name_get_uid)


class ProductProductInherit(models.Model):
    _inherit = "product.product"

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):

        # Get the connected user
        user = self.env.user

        domain = None

        if not self.env.is_admin():
            domain = [('partner_id.user_ids', 'like', user.id)]

        return super(ProductProductInherit, self).search_read(domain, fields, offset, limit, order)

    @api.model
    def _name_search(self, name, args=None, operator="ilike", limit=100, name_get_uid=None):
        args = args or []

        domain = []

        # Get the brand id
        brand_id = self.env.context.get('brand_id')

        # Get the connected user
        user = self.env.user

        if not self.env.is_admin():
            domain = [('partner_id.user_ids', 'like', user.id)]
        if brand_id:
            domain += [('brand_id', '=', brand_id)]

        return self._search(domain+args, limit=limit, access_rights_uid=name_get_uid)
