from odoo import api, models


class RelatedProductionReport(models.AbstractModel):
    _name = "report.rcp_powder_coating.report_related_production"

    @api.model
    def _get_report_values(self, doc_ids, data=None):
        production_ids = self.env['mrp.production'].browse(doc_ids)
        production_id_dict = {}
        for production_id in production_ids:
            production_ids = [production_id]
            production_id_dict[production_id.name] = self._get_related_production_ids(production_ids)
        return {"production_id_dict": production_id_dict}

    def _get_related_production_ids(self, production_ids):
        origin = production_ids[-1].origin
        parent = self.env['mrp.production'].search([('name', '=', origin)])
        if parent:
            production_ids.append(parent)
            production_ids = self._get_related_production_ids(production_ids)
        return production_ids
