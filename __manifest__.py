# -*- coding: utf-8 -*-
{
    "name": "Powder Coating",
    "summary": "Application to assist in managing transfers of parts to and from powder coat vendor",
    "author": "Sam Audia",
    "license": "AGPL-3",
    "version": "15.0",
    "depends": ["base", "mail", "stock"],
    "application": True,
    "data": [
        "security/powder_coating_security.xml",
        "security/ir.model.access.csv",
        "reports/report_picking.xml",
        "reports/report_related_production.xml",
        "reports/report_package_barcode_extend.xml"
    ],
    "category": "RCP/Powder Coating",
}
