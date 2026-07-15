{
    "name": "Professional Product Sales Report",
    "summary": "Bilingual daily, weekly, monthly, and custom product sales PDF report",
    "version": "19.0.1.0.4",
    "category": "Sales/Reporting",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": ["sale_management"],
    "data": [
        "security/ir.model.access.csv",
        "views/product_sales_report_wizard_views.xml",
        "report/product_sales_report_action.xml",
        "report/product_sales_report_templates.xml",
    ],
    "installable": True,
    "application": False,
}
