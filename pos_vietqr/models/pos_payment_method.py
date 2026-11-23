import secrets

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# NAPAS BINs of the most used banks. Check yours on the bank's VietQR page if it is missing.
VIETQR_BANKS = [
    ("970436", "Vietcombank"),
    ("970415", "VietinBank"),
    ("970418", "BIDV"),
    ("970405", "Agribank"),
    ("970407", "Techcombank"),
    ("970422", "MB Bank"),
    ("970416", "ACB"),
    ("970432", "VPBank"),
    ("970423", "TPBank"),
    ("970403", "Sacombank"),
    ("970437", "HDBank"),
    ("970441", "VIB"),
    ("970443", "SHB"),
    ("970431", "Eximbank"),
    ("970426", "MSB"),
    ("970448", "OCB"),
    ("970440", "SeABank"),
    ("970449", "LPBank"),
    ("970428", "Nam A Bank"),
    ("970454", "BVBank"),
]


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    vietqr_bank_bin = fields.Selection(VIETQR_BANKS, string="Bank")
    vietqr_account_number = fields.Char("Account number")
    vietqr_account_name = fields.Char("Account holder", help="Shown under the QR code so customers can check who they pay.")
    vietqr_webhook_key = fields.Char(
        "Webhook API key",
        copy=False,
        groups="point_of_sale.group_pos_manager",
        default=lambda self: secrets.token_urlsafe(24),
        help="Paste this key into SePay as the webhook API key. SePay sends it as 'Authorization: Apikey <key>'.",
    )
    vietqr_webhook_url = fields.Char("Webhook URL", compute="_compute_vietqr_webhook_url")

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [("vietqr", "VietQR")]

    def _compute_vietqr_webhook_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for method in self:
            method.vietqr_webhook_url = f"{base_url}/pos_vietqr/webhook/sepay"

    @api.constrains("use_payment_terminal", "journal_id", "vietqr_bank_bin", "vietqr_account_number")
    def _check_vietqr(self):
        for method in self.filtered(lambda m: m.use_payment_terminal == "vietqr"):
            if method.journal_id.type != "bank":
                raise ValidationError(_("VietQR payments go to a bank account: pick a Bank journal."))
            if not method.vietqr_bank_bin or not method.vietqr_account_number:
                raise ValidationError(_("VietQR needs a bank and an account number."))
            if not method.vietqr_account_number.isalnum():
                raise ValidationError(_("The account number may only contain letters and digits."))
