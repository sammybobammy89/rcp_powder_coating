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

    def action_receive_powder_coating(self):
        powder_coater_incoming_location_id = self.get_powder_coater_incoming_location_id()
        powder_coater_stock_location_id = self.get_powder_coater_stock_location_id()
        sm_stock_location_id = self.get_sm_stock_location_id()
        for rec in self:
            distinct_receipt_picking_ids = set(rec.env['stock.move.line'].search(
                [('package_id', '=', rec.id),
                 ('state', '=', 'assigned'),
                 ('picking_id.location_id', '=', powder_coater_incoming_location_id),
                 ('picking_id.location_dest_id', '=', powder_coater_stock_location_id)], order="id").mapped(
                "picking_id").mapped("id"))

            receipt_pickings = self.env['stock.picking'].browse(distinct_receipt_picking_ids)
            pc_mo_dict = {}
            for receipt_picking in receipt_pickings:

                for receipt_move_line in [x for x in receipt_picking.move_line_ids if x.package_id.id == rec.id]:
                    # get all completed move lines delivery from sheet metal stock with matching package and origin
                    delivery_move_lines = rec.env['stock.move.line'].search(
                        [('result_package_id', '=', rec.id),
                         ('state', '=', 'done'),
                         ('picking_id.location_id', '=', sm_stock_location_id),
                         ('picking_id.location_dest_id', '=', powder_coater_incoming_location_id),
                         ('picking_id.origin', '=', receipt_picking.origin)])
                    # update done quantities for receipt move lines
                    for delivery_move_line_id in delivery_move_lines:
                        receipt_move_line.qty_done = receipt_move_line.qty_done + delivery_move_line_id.qty_done

                    [pc_mo] = rec.env['mrp.production'].search([('state', 'not in', ['draft', 'done', 'cancel']),
                                                                ('name', 'like', receipt_picking.origin)])

                    pc_mo_dict.update({pc_mo.name: receipt_move_line.qty_done})

            # button validate must act on list of pickings all at once otherwise in the case of two deliveries
            # being in same bin will give error saying that you cannot move package to two places
            receipt_pickings.with_context({'skip_immediate': True, 'skip_backorder': True}).button_validate()


            for name, qty in pc_mo_dict.items():
                [pc_mo] = rec.env['mrp.production'].search([('name', '=', name)])


                move_complete = []
                for move in pc_mo.move_raw_ids:
                    move.quantity_done = move.quantity_done + qty
                    if move.quantity_done == move.product_uom_qty:
                        move_complete.append(True)
                    elif move.quantity_done > move.product_uom_qty:
                        raise UserError(_('Impossible to plan the workorder. Please check the workcenter availabilities.'))
                    else:
                        move_complete.append(False)

                if all(move_complete):
                    pc_mo.qty_producing = pc_mo.product_uom_qty
                    pc_mo.with_context({'skip_immediate': True, 'skip_backorder': True}).button_mark_done()
                # if backorder_qty > 0:
                #     pc_mo._split_productions({pc_mo: [qty, backorder_qty]})
                    # pc_mo._split_productions()
        # unpack bin
        # do backorder for mo, use mrp.production _split_productions method, does this complete mo as well?
        # create delivery back order stock.picking _create_backorder method for delivery
        # create delivery back order stock.picking _create_backorder method for receipt
