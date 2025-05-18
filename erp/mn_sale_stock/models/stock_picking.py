# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.depends('location_id')
    def _compute_domain_location_id(self):
        warehouses = self.env['stock.warehouse'].sudo().search([])
        picking_type_code = self.env.context.get('restricted_picking_type_code')
        for obj in self:
            ids = [x.id for x in warehouses.mapped('lot_stock_id')]
            obj.domain_location_id = []
            if picking_type_code == 'internal':
                obj.domain_location_id = [('id', 'in', ids), ('id', '!=', obj.location_id.id)]

    def _compute_total_qty(self):
        for obj in self:
            total_qty = 0
            for move in obj.move_ids_without_package:
                total_qty += move.quantity
            obj.total_qty = total_qty

    def _compute_total_price(self):
        for obj in self:
            total_price = 0
            for move in obj.move_ids_without_package:
                total_price += move.price_unit * move.quantity
            obj.total_price = total_price
                
    domain_location_id = fields.Binary('Location Domain', compute=_compute_domain_location_id)
    total_qty = fields.Float('Total Quantity', compute='_compute_total_qty')
    total_price = fields.Float('Total Quantity', compute='_compute_total_price')