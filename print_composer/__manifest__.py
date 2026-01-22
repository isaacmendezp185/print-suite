
{
    'name': 'Print Composer (Wizard)',
    'summary': 'Asistente de composición para crear trabajos de impresión',
    'version': '18.0.1.2.0',
    'author': 'Isaac Mendez • Suite de Impresión',
    'license': 'LGPL-3',
    'category': 'Manufacturing/Manufacturing',
    'depends': [
        'base',
        'mail',
        'product',
        'sale',                 # integración ventas
        'mrp',
        'print_workcenters',
        'print_materials',
        'print_job_manager',
        'print_costing_engine',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/composer_views.xml',
        'views/sale_integration_views.xml',
        'views/sale_order_statbutton_views.xml',  # <-- NUEVO
    ],
    'installable': True,
    'application': False,
}


