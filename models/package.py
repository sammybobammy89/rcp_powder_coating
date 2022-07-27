from odoo import fields, models, api, _
from odoo.exceptions import UserError


class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"
    weight_out_lbs = fields.Float("Weight Outgoing (lbs)")
    weight_in_lbs = fields.Float("Weight Incoming (lbs)")

    is_in_powder_coater_incoming = fields.Boolean(string="In Powder Coater Incoming Location", required=True,
                                                  compute="compute_is_in_powder_coater_incoming")

    @api.depends("name", "location_id")
    def compute_is_in_powder_coater_incoming(self):
        powder_coater_incoming_location_id = int(
            self.env['ir.config_parameter'].get_param('rcp_powder_coating.powder_coater_incoming_location_id'))
        for rec in self:
            rec.is_in_powder_coater_incoming = rec.location_id.id == powder_coater_incoming_location_id

    def container_validate_picking(self):
        for rec in self:
            if rec.picking_id:
                # move to picking not one2one if complete previously do not try to complete again
                if rec.picking_id.state == 'done':
                    continue
                # complete picking
                rec.picking_id.action_assign()
                for move_line in rec.picking_id.mapped('move_line_ids_without_package'):
                    move_line.qty_done = move_line.product_uom_qty
                rec.picking_id.button_validate()

    def button_receive_from_powder_coater(self):
        selected_ids = self.env.context.get('active_ids', [])
        self.search([('id', 'in', selected_ids)]).receive_from_powder_coater()

    def get_powder_coater_incoming_location_id(self):
        return int(self.env['ir.config_parameter'].get_param('rcp_powder_coating.powder_coater_incoming_location_id'))

    def get_powder_coater_stock_location_id(self):
        return int(self.env['ir.config_parameter'].get_param('rcp_powder_coating.powder_coater_stock_location_id'))

    def get_sm_stock_location_id(self):
        return int(self.env['ir.config_parameter'].get_param('rcp_powder_coating.sm_stock_location_id'))

    def get_coated_product_id(self, uncoated_product_id):
        coated_product_name = uncoated_product_id.name.rstrip('_uc')
        [product_id] = self.env['product.product'].search([('name', '=', coated_product_name)])
        return product_id

    def get_move_lines_state_location_origin(self, state, location_id, location_dest_id, origin):
        return self.env['stock.move.line'].search(
            [('result_package_id', '=', self.id),
             ('state', '=', state),
             ('picking_id.location_id', '=', location_id),
             ('picking_id.location_dest_id', '=', location_dest_id),
             ('picking_id.origin', '=', origin)])

    def get_picking_ids_by_package_state_location(self, state, location_id, location_dest_id):
        picking_ids = set(self.env['stock.move.line'].search(
            [('package_id', '=', self.id),
             ('state', '=', state),
             ('picking_id.location_id', '=', location_id),
             ('picking_id.location_dest_id', '=', location_dest_id)], order="id").mapped("picking_id").mapped("id"))
        return self.env['stock.picking'].browse(picking_ids)

    def get_move_line_by_state_product_location_origins(self, ok_state_list, product_id, location_id, origin):
        [move_line] = self.env['stock.move.line'].search([('state', 'in', ok_state_list),
                                                          ('product_id', '=', product_id),
                                                          ('picking_id.location_id', '=', location_id),
                                                          ('picking_id.origin', '=', origin)], order="id")
        return move_line

    def receive_uncoated_parts_at_powder_coater(self, powder_coater_receipts):
        for powder_coater_receipt in powder_coater_receipts:
            for move_line in [x for x in powder_coater_receipt.move_line_ids if x.package_id.id == self.id]:
                delivery_move_lines = self.get_move_lines_state_location_origin('done',
                                                                                self.get_sm_stock_location_id(),
                                                                                self.get_powder_coater_incoming_location_id(),
                                                                                powder_coater_receipt.origin)
                for delivery_move_line_id in delivery_move_lines:
                    move_line.qty_done = move_line.qty_done + delivery_move_line_id.qty_done
        # button validate must act on list of pickings all at once otherwise in the case of two deliveries
        # being in same bin will give error saying that you cannot move package to two places
        powder_coater_receipts.with_context({'skip_immediate': True, 'skip_backorder': True}).button_validate()
        return True

    def set_powder_coat_delivery_packages_and_quantities(self, powder_coater_mos):
        for powder_coater_mo in powder_coater_mos:
            [delivery_move_line] = self.get_move_line_by_state_product_location_origins(
                ['assigned', 'partially_available'],
                powder_coater_mo.product_id.id,
                self.get_powder_coater_stock_location_id(),
                powder_coater_mo.origin)

            delivery_move_line.result_package_id = self.id
            delivery_move_line.qty_done = powder_coater_mo.qty_producing

        return True

    def get_deliveries_from_powder_coater(self, origins):
        return self.env['stock.picking'].search([('state', '=', 'assigned'),
                                                 ('location_id', '=',
                                                  self.get_powder_coater_stock_location_id()),
                                                 ('origin', 'in', origins)])

    def get_coated_receipts(self, origins):
        return self.env['stock.move.line'].search([('picking_id.state', '=', 'assigned'),
                                                   ('package_id', '=', self.id),
                                                   ('origin', 'in', origins)]).mapped("picking_id")

    def complete_powder_coating_manufacturing_orders(self, powder_coater_receipts):
        pc_mo_ids = []
        for receipt_picking in powder_coater_receipts:
            for receipt_move_line in [x for x in receipt_picking.move_line_ids if x.package_id.id == self.id]:
                [pc_mo] = self.env['mrp.production'].search([('state', 'not in', ['draft', 'done', 'cancel']),
                                                             ('name', 'like', receipt_picking.origin + '%')])
                pc_mo.qty_producing = receipt_move_line.qty_done
                if pc_mo.qty_producing != pc_mo.product_uom_qty:
                    pc_mo._split_productions()
                for move in pc_mo.move_raw_ids:
                    move.quantity_done = pc_mo.qty_producing
                pc_mo.with_context({'skip_immediate': True, 'skip_backorder': True}).button_mark_done()
                pc_mo_ids.append(pc_mo.id)

        return self.env['mrp.production'].browse(set(pc_mo_ids))

    def action_receive_powder_coating(self):
        for rec in self:
            powder_coater_receipts = rec.get_picking_ids_by_package_state_location(
                'assigned',
                rec.get_powder_coater_incoming_location_id(),
                rec.get_powder_coater_stock_location_id())

            rec.receive_uncoated_parts_at_powder_coater(powder_coater_receipts)
            powder_coater_mos = rec.complete_powder_coating_manufacturing_orders(powder_coater_receipts)
            rec.set_powder_coat_delivery_packages_and_quantities(powder_coater_mos)
            origins = powder_coater_mos.mapped('origin')
            powder_coater_deliveries = rec.get_deliveries_from_powder_coater(origins)
            powder_coater_deliveries.with_context({'skip_immediate': True,
                                                   'skip_backorder': True,
                                                   'skip_sms': True}).button_validate()

            coated_part_receipts = rec.get_coated_receipts(origins)
            coated_part_receipts.action_set_quantities_to_reservation()
            coated_part_receipts.with_context({'skip_immediate': True,
                                               'skip_backorder': True,
                                               'skip_sms': True}).button_validate()
