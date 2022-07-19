from odoo import fields, models


class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"
    weight_out_lbs = fields.Float("Weight Outgoing (lbs)")
    weight_in_lbs = fields.Float("Weight Incoming (lbs)")
