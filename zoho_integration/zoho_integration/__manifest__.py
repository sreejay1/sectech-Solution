{
    'name': 'Zoho Inventory Connector',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Effortlessly sync products from Zoho Inventory to Odoo 17+. Features include automated scheduling, user-friendly configuration, robust security, and scalability. Integrates Zoho Inventory tools with Odoo ERP for seamless inventory management.',
    'author': 'Zerone Consulting',
    'depends': ['base', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/zoho_config_views.xml',
        'data/cron_jobs.xml',
    ],
    'installable': True,
    'application': True,
}
