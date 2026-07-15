from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductSalesReportWizard(models.TransientModel):
    _name = "product.sales.report.wizard"
    _description = "Product Sales Report Wizard"

    period_type = fields.Selection(
        selection=[
            ("day", "Day"),
            ("week", "Week"),
            ("month", "Month"),
            ("custom", "Custom Range"),
        ],
        string="Period",
        required=True,
        default="day",
    )
    report_date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
    )
    date_from = fields.Date(string="Start Date")
    date_to = fields.Date(string="End Date")
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    @api.constrains("period_type", "report_date", "date_from", "date_to")
    def _check_dates(self):
        for wizard in self:
            if wizard.period_type == "custom":
                if not wizard.date_from or not wizard.date_to:
                    raise ValidationError(_("Start Date and End Date are required for a custom range."))
                if wizard.date_from > wizard.date_to:
                    raise ValidationError(_("Start Date cannot be after End Date."))
            elif not wizard.report_date:
                raise ValidationError(_("Date is required for the selected period."))

    def _get_period_dates(self):
        self.ensure_one()
        if self.period_type == "custom":
            date_from = self.date_from
            date_to = self.date_to
        elif self.period_type == "day":
            date_from = date_to = self.report_date
        elif self.period_type == "week":
            date_from = self.report_date - timedelta(days=self.report_date.weekday())
            date_to = date_from + timedelta(days=6)
        else:
            date_from = self.report_date.replace(day=1)
            next_month = (date_from.replace(day=28) + timedelta(days=4)).replace(day=1)
            date_to = next_month - timedelta(days=1)
        return date_from, date_to

    def _get_utc_datetime_bounds(self, date_from, date_to):
        self.ensure_one()
        timezone = pytz.timezone(self.env.user.tz or "UTC")
        local_start = timezone.localize(datetime.combine(date_from, time.min))
        local_end = timezone.localize(datetime.combine(date_to + timedelta(days=1), time.min))
        return (
            local_start.astimezone(pytz.UTC).replace(tzinfo=None),
            local_end.astimezone(pytz.UTC).replace(tzinfo=None),
        )

    def action_print_report(self):
        self.ensure_one()
        self._check_dates()
        date_from, date_to = self._get_period_dates()
        datetime_from, datetime_to = self._get_utc_datetime_bounds(date_from, date_to)
        data = {
            "wizard_id": self.id,
            "period_type": self.period_type,
            "date_from": fields.Date.to_string(date_from),
            "date_to": fields.Date.to_string(date_to),
            "datetime_from": fields.Datetime.to_string(datetime_from),
            "datetime_to": fields.Datetime.to_string(datetime_to),
            "company_id": self.company_id.id,
        }
        return self.env.ref(
            "sale_daily_product_report.action_product_sales_report"
        ).report_action(self, data=data)
