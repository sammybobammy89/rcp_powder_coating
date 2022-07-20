from odoo import fields, models


class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"
    weight_out_lbs = fields.Float("Weight Outgoing (lbs)")
    weight_in_lbs = fields.Float("Weight Incoming (lbs)")

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

    def receive_from_powder_coater(self):
        for rec in self:
            # todo receive from powder coater code
            # check to make sure all pack is at powder coater
            # idenity 8 digit parts
            # unpack bin
            # do backorder for mo, use mrp.production _split_productions method, does this complete mo as well?
            # create delivery back order stock.picking _create_backorder method for delivery
            # create delivery back order stock.picking _create_backorder method for receipt
            print()

