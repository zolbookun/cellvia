# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockWarehouseOrderPoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    @api.depends('location_id')
    def _compute_domain_location_id(self):
        warehouses = self.env['stock.warehouse'].sudo().search([])
        for obj in self:
            obj.domain_location_id = []
            ids = [x.id for x in warehouses.mapped('lot_stock_id')]
            obj.domain_location_id = [('id', 'in', ids)]

    domain_location_id = fields.Binary('Location Domain', compute=_compute_domain_location_id)