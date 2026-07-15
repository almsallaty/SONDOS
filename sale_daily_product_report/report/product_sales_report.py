from collections import defaultdict

from odoo import _, api, fields, models
from odoo.tools.misc import format_date


class ProductSalesReport(models.AbstractModel):
    _name = "report.sale_daily_product_report.product_sales_report_document"
    _description = "Product Sales Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        lang = self.env.user.lang or "en_US"
        # Force all Python translations to use the printing user's language.
        report_self = self.with_context(lang=lang)

        wizard = report_self.env["product.sales.report.wizard"].browse(data.get("wizard_id")).exists()
        company = report_self.env["res.company"].browse(data.get("company_id")).exists() or report_self.env.company

        date_from = fields.Date.to_date(data["date_from"])
        date_to = fields.Date.to_date(data["date_to"])
        datetime_from = fields.Datetime.to_datetime(data["datetime_from"])
        datetime_to = fields.Datetime.to_datetime(data["datetime_to"])

        order_domain = [
            ("company_id", "=", company.id),
            ("state", "in", ["sale", "done"]),
            ("date_order", ">=", datetime_from),
            ("date_order", "<", datetime_to),
        ]
        orders = report_self.env["sale.order"].with_company(company).search(
            order_domain, order="date_order, id"
        )

        line_domain = [
            ("order_id", "in", orders.ids),
            ("display_type", "=", False),
            ("product_id", "!=", False),
        ]
        if "is_downpayment" in report_self.env["sale.order.line"]._fields:
            line_domain.append(("is_downpayment", "=", False))
        lines = report_self.env["sale.order.line"].with_company(company).search(line_domain)

        grouped = defaultdict(
            lambda: {
                "product": report_self.env["product.product"],
                "uom": report_self.env["uom.uom"],
                "order_ids": set(),
                "quantity": 0.0,
                "sales_total": 0.0,
            }
        )
        total_sales = 0.0

        for line in lines:
            key = (line.product_id.id, line.product_uom_id.id)
            bucket = grouped[key]
            # display_default_code=False avoids repeating the reference in both
            # the Product and Internal Reference columns while retaining the
            # standard translated display_name implementation.
            bucket["product"] = line.product_id.with_context(
                lang=lang, display_default_code=False
            )
            bucket["uom"] = line.product_uom_id.with_context(lang=lang)
            bucket["order_ids"].add(line.order_id.id)
            bucket["quantity"] += line.product_uom_qty

            converted_total = line.order_id.currency_id._convert(
                line.price_total,
                company.currency_id,
                company,
                line.order_id.date_order.date(),
            )
            bucket["sales_total"] += converted_total
            total_sales += converted_total

        report_lines = []
        for values in grouped.values():
            report_lines.append(
                {
                    "product": values["product"],
                    "default_code": values["product"].default_code or "",
                    "order_count": len(values["order_ids"]),
                    "quantity": values["quantity"],
                    "uom": values["uom"],
                    "sales_total": values["sales_total"],
                }
            )
        report_lines.sort(key=lambda item: (item["product"].display_name or "").casefold())

        order_count = len(orders)


        return {
            "doc_ids": wizard.ids,
            "doc_model": "product.sales.report.wizard",
            "docs": wizard,
            "company": company.with_context(lang=lang),
            "currency": company.currency_id.with_context(lang=lang),
            "date_from": date_from,
            "date_to": date_to,
            "date_from_display": format_date(report_self.env, date_from, lang_code=lang),
            "date_to_display": format_date(report_self.env, date_to, lang_code=lang),
            "period_type": data.get("period_type", "custom"),
            "report_lines": report_lines,
            "order_count": order_count,
            "product_count": len({line.product_id.id for line in lines}),
            "total_sales": total_sales,
            "average_order_value": total_sales / order_count if order_count else 0.0,
            "printed_by": report_self.env.user.with_context(lang=lang),
            "is_rtl": lang.lower().startswith("ar"),
            "report_lang": lang,
        }
