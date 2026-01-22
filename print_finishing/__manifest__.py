
{
    'name': 'Print Finishing',
    'summary': 'Acabados (laminado, corte, costura, ojillos, empaque) para trabajos de impresión',
    'version': '18.0.1.0.0',
    'author': 'Isaac Mendez • Suite de Impresión',
    'license': 'LGPL-3',
    'category': 'Manufacturing/Manufacturing',
    'depends': [
        'base',
        'mrp',
        'print_workcenters',
        'print_materials',
        'print_job_manager',
        'print_costing_engine',   # para extender action_estimate_costs
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/finishing_views.xml',
    ],
    'installable': True,
    'application': False,
}


