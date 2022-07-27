from odoo import _, api, fields, models
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError


class Picking(models.Model):
    _inherit = "stock.picking"

    sourced_from_sm_stock_location = fields.Boolean(string="Shipping from Sheet Metal Stock Location", required=True,
                                                    compute="compute_sm_stock_location")

    is_origin_mo_229_kit = fields.Boolean(string="Is Origin of Picking a 229 Kit", required=True,
                                          compute="compute_is_origin_mo_229_kit")

    contains_single_product = fields.Boolean(string="Contains Single Product", required=True,
                                             compute="compute_contains_single_product")

    contains_uc_products = fields.Boolean(string="Contains Only _uc Products", required=True,
                                          compute="compute_contains_uc_products")

    @api.depends("name", "location_id")
    def compute_sm_stock_location(self):
        sm_stock_location_id = int(self.env['ir.config_parameter'].get_param('rcp_powder_coating.sm_stock_location_id'))
        for rec in self:
            rec.sourced_from_sm_stock_location = rec.location_id.id == sm_stock_location_id

    @api.depends("sourced_from_sm_stock_location")
    def compute_is_origin_mo_229_kit(self):
        for rec in self:
            rec.is_origin_mo_229_kit = False

            if '/MO/' not in rec.origin or not rec.sourced_from_sm_stock_location:
                return

            try:
                [mo] = rec.env['mrp.production'].search([('name', '=', rec.origin)])
                rec.is_origin_mo_229_kit = mo.product_id.name[0:3] == '229'
            except:
                pass

    @api.depends("sourced_from_sm_stock_location")
    def compute_contains_single_product(self):
        for rec in self:
            products = set(rec.move_line_ids.mapped("product_id"))
            rec.contains_single_product = True if len(products) == 1 else False

    @api.depends("sourced_from_sm_stock_location")
    def compute_contains_uc_products(self):
        for rec in self:
            products = set(rec.move_line_ids.mapped("product_id"))
            rec.contains_uc_products = all([(x.name[-3:] == '_uc') for x in products])

    def _put_in_pc_pack(self, move_line_ids, create_package_level, powder_coating_shipment=False):
        package = self._put_in_pack(move_line_ids, create_package_level)
        if powder_coating_shipment:
            package.package_type_id = self.env['ir.config_parameter'].get_param('rcp_powder_coating.pc_package_type_id')
            # package.name = package.name.replace("PACK", "PC")
        return package

    def _put_in_pc_229_pack(self, move_line_ids, create_package_level, powder_coating_shipment=False):
        package = self._put_in_pack(move_line_ids, create_package_level)
        if powder_coating_shipment:
            package.package_type_id = self.env['ir.config_parameter'].get_param(
                'rcp_powder_coating.pc_229_package_type_id')
            # package.name = package.name.replace("PACK", "PC")
        return package

    def action_put_in_pc_pack(self):
        self.ensure_one()
        if self.state not in ('done', 'cancel'):
            picking_move_lines = self.move_line_ids
            if (
                    not self.picking_type_id.show_reserved
                    and not self.immediate_transfer
                    and not self.env.context.get('barcode_view')
            ):
                picking_move_lines = self.move_line_nosuggest_ids

            move_line_ids = picking_move_lines.filtered(lambda ml:
                                                        float_compare(ml.qty_done, 0.0,
                                                                      precision_rounding=ml.product_uom_id.rounding) > 0
                                                        and not ml.result_package_id
                                                        )
            if not move_line_ids:
                move_line_ids = picking_move_lines.filtered(lambda ml: float_compare(ml.product_uom_qty, 0.0,
                                                                                     precision_rounding=ml.product_uom_id.rounding) > 0 and float_compare(
                    ml.qty_done, 0.0,
                    precision_rounding=ml.product_uom_id.rounding) == 0)
            if move_line_ids:
                res = self._pre_put_in_pack_hook(move_line_ids)
                if not res:
                    res = self._put_in_pc_pack(move_line_ids, True, True)
                return res
            else:
                raise UserError(_("Please add 'Done' quantities to the picking to create a new pack."))

    def action_put_in_pc_pack_separate(self):
        self.ensure_one()
        if self.state not in ('done', 'cancel'):
            picking_move_lines = self.move_line_ids
            if (
                    not self.picking_type_id.show_reserved
                    and not self.immediate_transfer
                    and not self.env.context.get('barcode_view')
            ):
                picking_move_lines = self.move_line_nosuggest_ids

            move_line_ids = picking_move_lines.filtered(lambda ml:
                                                        float_compare(ml.qty_done, 0.0,
                                                                      precision_rounding=ml.product_uom_id.rounding) > 0
                                                        and not ml.result_package_id
                                                        )
            if not move_line_ids:
                move_line_ids = picking_move_lines.filtered(lambda ml: float_compare(ml.product_uom_qty, 0.0,
                                                                                     precision_rounding=ml.product_uom_id.rounding) > 0 and float_compare(
                    ml.qty_done, 0.0,
                    precision_rounding=ml.product_uom_id.rounding) == 0)
            if move_line_ids:
                res = self._pre_put_in_pack_hook(move_line_ids)
                if not res:
                    for move_line_id in move_line_ids:
                        res = self._put_in_pc_pack([move_line_id], True, True)
                return res
            else:
                raise UserError(_("Please add 'Done' quantities to the picking to create a new pack."))


    def action_put_in_pc_229_pack(self):
        self.ensure_one()
        if self.state not in ('done', 'cancel'):
            picking_move_lines = self.move_line_ids
            if (
                    not self.picking_type_id.show_reserved
                    and not self.immediate_transfer
                    and not self.env.context.get('barcode_view')
            ):
                picking_move_lines = self.move_line_nosuggest_ids

            move_line_ids = picking_move_lines.filtered(lambda ml:
                                                        float_compare(ml.qty_done, 0.0,
                                                                      precision_rounding=ml.product_uom_id.rounding) > 0
                                                        and not ml.result_package_id
                                                        )
            if not move_line_ids:
                move_line_ids = picking_move_lines.filtered(lambda ml: float_compare(ml.product_uom_qty, 0.0,
                                                                                     precision_rounding=ml.product_uom_id.rounding) > 0 and float_compare(
                    ml.qty_done, 0.0,
                    precision_rounding=ml.product_uom_id.rounding) == 0)
            if move_line_ids:
                res = self._pre_put_in_pack_hook(move_line_ids)
                if not res:
                    res = self._put_in_pc_229_pack(move_line_ids, True, True)
                return res
            else:
                raise UserError(_("Please add 'Done' quantities to the picking to create a new pack."))

    def action_put_in_pc_229_pack_separate(self):
        self.ensure_one()
        if self.state not in ('done', 'cancel'):
            picking_move_lines = self.move_line_ids
            if (
                    not self.picking_type_id.show_reserved
                    and not self.immediate_transfer
                    and not self.env.context.get('barcode_view')
            ):
                picking_move_lines = self.move_line_nosuggest_ids

            move_line_ids = picking_move_lines.filtered(lambda ml:
                                                        float_compare(ml.qty_done, 0.0,
                                                                      precision_rounding=ml.product_uom_id.rounding) > 0
                                                        and not ml.result_package_id
                                                        )
            if not move_line_ids:
                move_line_ids = picking_move_lines.filtered(lambda ml: float_compare(ml.product_uom_qty, 0.0,
                                                                                     precision_rounding=ml.product_uom_id.rounding) > 0 and float_compare(
                    ml.qty_done, 0.0,
                    precision_rounding=ml.product_uom_id.rounding) == 0)
            if move_line_ids:
                res = self._pre_put_in_pack_hook(move_line_ids)
                if not res:
                    for move_line_id in move_line_ids:
                        res = self._put_in_pc_229_pack([move_line_id], True, True)
                return res
            else:
                raise UserError(_("Please add 'Done' quantities to the picking to create a new pack."))

    def action_put_in_pack_separate(self):
        self.ensure_one()
        if self.state not in ('done', 'cancel'):
            picking_move_lines = self.move_line_ids
            if (
                    not self.picking_type_id.show_reserved
                    and not self.immediate_transfer
                    and not self.env.context.get('barcode_view')
            ):
                picking_move_lines = self.move_line_nosuggest_ids

            move_line_ids = picking_move_lines.filtered(lambda ml:
                                                        float_compare(ml.qty_done, 0.0,
                                                                      precision_rounding=ml.product_uom_id.rounding) > 0
                                                        and not ml.result_package_id
                                                        )
            if not move_line_ids:
                move_line_ids = picking_move_lines.filtered(lambda ml: float_compare(ml.product_uom_qty, 0.0,
                                                                                     precision_rounding=ml.product_uom_id.rounding) > 0 and float_compare(
                    ml.qty_done, 0.0,
                    precision_rounding=ml.product_uom_id.rounding) == 0)
            if move_line_ids:
                res = self._pre_put_in_pack_hook(move_line_ids)
                if not res:
                    for move_line_id in move_line_ids:
                        res = self._put_in_pack([move_line_id])
                return res
            else:
                raise UserError(_("Please add 'Done' quantities to the picking to create a new pack."))
