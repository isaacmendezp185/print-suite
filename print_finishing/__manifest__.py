{
    'name': 'Print Finishing',
    'summary': 'Acabados (laminado, corte, costura, ojillos, empaque) para trabajos de impresión',
    'version': '18.0.2.0.0',
    'author': 'Isaac Mendez • Suite de Impresión',
    'license': 'LGPL-3',
    'category': 'Manufacturing/Manufacturing',
    'depends': [
        'base',
        'mrp',
        'print_workcenters',
        'print_materials',
        'print_job_manager',
        'print_costing_engine',
    ],
    
'data': [
    'security/ir.model.access.csv',
    'views/finishing_template_views.xml',         # 1) Configuración (ok)
    'views/finishing_apply_template_wizard.xml',  # 2) CREA la acción
    'views/finishing_views.xml',                  # 3) Usa la acción (ya existe)
],

    'installable': True,
    'application': False,
}





