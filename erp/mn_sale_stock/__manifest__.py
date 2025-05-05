# -*- coding: utf-8 -*-
{
    'name': 'Mongolian Sale Stock',
    'version': '17.0',
    'category': 'Mongolian Modules',
    'summary': 'This module allows you to smartly manage sale stock.',
    'description': 'Sale Stock.',
    'author': 'Z',
    'company': 'Z',
    'maintainer': 'Z',
    'website': '',
    'depends': ['sale_stock', 'stock'],
    "data": [
        'security/security.xml',
        'views/stock_menus.xml',
        'views/stock_picking_views.xml',
        'views/stock_warehouse_orderpoint_views.xml'
    ],
    'license': 'GPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
