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

    def button_autoschedule(self):
        selected_ids = self.env.context.get('active_ids', [])
        self.search([('id', 'in', selected_ids)]).autoschedule()

    def autoschedule(self):
        for rec in self:
            containers = rec.env['rcp_container.container'].search([('date_departure', '<=', rec.date_deadline),
                                                                    ('state', '=', 'draft'),
                                                                    ('air_freight', '=', False),
                                                                    ('container_vendor_id.receipt_picking_type_id', '=',
                                                                     rec.picking_type_id.id)],
                                                                   order='date_departure desc')
            if containers:
                rec.container_id = containers[0].id

