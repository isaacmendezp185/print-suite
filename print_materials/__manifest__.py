{
    'name': 'Print Materials',
    'summary': 'Sustratos, tintas y máquinas para impresión gran formato',
    'version': '18.0.1.0.0',
    'author': 'Isaac Mendez • Suite de Impresión',
    'license': 'LGPL-3',
    'category': 'Manufacturing/Manufacturing',
    'depends': [
        'base',
        'product',
        'mrp',
        'print_workcenters',  # para menús y relación con workcenter
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/print_substrate_views.xml',
        'views/print_ink_views.xml',
        'views/print_machine_views.xml',
        'data/materials_data.xml',
    ],
    'installable': True,
    'application': False,
}
