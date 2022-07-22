from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = ['res.config.settings']

    package_type_id = fields.Many2one("stock.package.type", string="Powder Coating Shipment Package Type",
                                      config_parameter="rcp_powder_coating.package_type_id")
    powder_coater_incoming_location_id = fields.Many2one("stock.location", string="Powder Coater Stock Location",
                                                         config_parameter="rcp_powder_coating.powder_coater_incoming_location_id")
    powder_coater_stock_location_id = fields.Many2one("stock.location", string="Powder Coater Stock Location",
                                                      config_parameter="rcp_powder_coating.powder_coater_stock_location_id")
    sm_stock_location_id = fields.Many2one("stock.location", string="Powder Coater Stock Location",
                                           config_parameter="rcp_powder_coating.sm_stock_location_id")
