
{
    'name': 'Print Costing Engine',
    'summary': 'Cálculo de costos para trabajos de impresión (material, tinta, máquina y acabados)',
    'version': '18.0.1.0.0',
    'author': 'Isaac Mendez • Suite de Impresión',
    'license': 'LGPL-3',
    'category': 'Manufacturing/Manufacturing',
    'depends': [
        'base',
        'print_materials',     # sustratos, tintas y máquinas
        'print_job_manager',   # print.job (área, calidad, vínculos)
    ],
    'data': [
        'views/print_job_costing_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
}
