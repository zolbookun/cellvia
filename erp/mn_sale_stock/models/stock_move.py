# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import Counter, defaultdict

from odoo import _, api, fields, tools, models, Command
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import OrderedSet, groupby
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.depends('price_unit', 'quantity')
    def _compute_amount_total(self):
        for obj in self:
            obj.amount_total = obj.price_unit * obj.quantity

    amount_total = fields.Float('Нийт дүн', compute=_compute_amount_total)

class StockMove(models.Model):
    _inherit = 'stock.move.line'

    price_unit = fields.Float('Нэгж үнэ', related='move_id.price_unit')

    def _get_aggregated_product_quantities(self, **kwargs):
        """ Returns a dictionary of products (key = id+name+description+uom+packaging) and corresponding values of interest.

        Allows aggregation of data across separate move lines for the same product. This is expected to be useful
        in things such as delivery reports. Dict key is made as a combination of values we expect to want to group
        the products by (i.e. so data is not lost). This function purposely ignores lots/SNs because these are
        expected to already be properly grouped by line.

        returns: dictionary {product_id+name+description+uom+packaging: {product, name, description, quantity, product_uom, packaging}, ...}
        """
        aggregated_move_lines = {}


        # Loops to get backorders, backorders' backorders, and so and so...
        backorders = self.env['stock.picking']
        pickings = self.picking_id
        while pickings.backorder_ids:
            backorders |= pickings.backorder_ids
            pickings = pickings.backorder_ids

        for move_line in self:
            if kwargs.get('except_package') and move_line.result_package_id:
                continue
            aggregated_properties = self._get_aggregated_properties(move_line=move_line)
            line_key, uom = aggregated_properties['line_key'], aggregated_properties['product_uom']
            quantity = move_line.product_uom_id._compute_quantity(move_line.quantity, uom)
            if line_key not in aggregated_move_lines:
                qty_ordered = None
                if backorders and not kwargs.get('strict'):
                    qty_ordered = move_line.move_id.product_uom_qty
                    # Filters on the aggregation key (product, description and uom) to add the
                    # quantities delayed to backorders to retrieve the original ordered qty.
                    following_move_lines = backorders.move_line_ids.filtered(
                        lambda ml: self._get_aggregated_properties(move=ml.move_id)['line_key'] == line_key
                    )
                    qty_ordered += sum(following_move_lines.move_id.mapped('product_uom_qty'))
                    # Remove the done quantities of the other move lines of the stock move
                    previous_move_lines = move_line.move_id.move_line_ids.filtered(
                        lambda ml: self._get_aggregated_properties(move=ml.move_id)['line_key'] == line_key and ml.id != move_line.id
                    )
                    qty_ordered -= sum([m.product_uom_id._compute_quantity(m.quantity, uom) for m in previous_move_lines])
                aggregated_move_lines[line_key] = {
                    **aggregated_properties,
                    'quantity': quantity,
                    'qty_ordered': qty_ordered or quantity,
                    'product': move_line.product_id,
                    'amount_total': move_line.quantity * move_line.price_unit,
                    'price_unit': move_line.price_unit,
                }
            else:
                aggregated_move_lines[line_key]['qty_ordered'] += quantity
                aggregated_move_lines[line_key]['quantity'] += quantity

        # Does the same for empty move line to retrieve the ordered qty. for partially done moves
        # (as they are splitted when the transfer is done and empty moves don't have move lines).
        if kwargs.get('strict'):
            return self._compute_packaging_qtys(aggregated_move_lines)
        pickings = (self.picking_id | backorders)
        for empty_move in pickings.move_ids:
            to_bypass = False
            if not (empty_move.product_uom_qty and float_is_zero(empty_move.quantity, precision_rounding=empty_move.product_uom.rounding)):
                continue
            if empty_move.state != "cancel":
                if empty_move.state != "confirmed" or empty_move.move_line_ids:
                    continue
                else:
                    to_bypass = True
            aggregated_properties = self._get_aggregated_properties(move=empty_move)
            line_key = aggregated_properties['line_key']

            if line_key not in aggregated_move_lines and not to_bypass:
                qty_ordered = empty_move.product_uom_qty
                aggregated_move_lines[line_key] = {
                    **aggregated_properties,
                    'quantity': False,
                    'qty_ordered': qty_ordered,
                    'product': empty_move.product_id,
                    'amount_total': move_line.quantity * move_line.price_unit,
                    'price_unit': move_line.price_unit,
                }
            elif line_key in aggregated_move_lines:
                aggregated_move_lines[line_key]['qty_ordered'] += empty_move.product_uom_qty

        return self._compute_packaging_qtys(aggregated_move_lines)