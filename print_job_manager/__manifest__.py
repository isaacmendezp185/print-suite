{
    'name': 'Print Job Manager',
    'summary': 'Gestión de trabajos de impresión gran formato',
    'version': '18.0.1.0.0',
    'author': 'Isaac Mendez • Suite de Impresión',
    'license': 'LGPL-3',
    'category': 'Manufacturing/Manufacturing',
    'depends': [
        'base',
        'mail',
        'mrp',
        'product',
        'print_workcenters',
        'print_materials',
    ],
    'data': [
        'data/sequence.xml',
        'security/ir.model.access.csv',
        'views/print_job_views.xml',
    ],
    'installable': True,
    'application': False,
}
