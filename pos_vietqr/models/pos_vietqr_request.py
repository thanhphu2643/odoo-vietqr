import secrets
import string

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..vietqr import build_payload

# No 0/O or 1/I, so a cashier can read a code aloud or type it without mistakes.
CODE_ALPHABET = "".join(c for c in string.ascii_uppercase + string.digits if c not in "01IO")
CODE_PREFIX = "VQR"


class PosVietqrRequest(models.Model):
    _name = "pos.vietqr.request"
    _description = "VietQR payment request"
    _order = "id desc"
    _rec_name = "code"

    code = fields.Char(required=True, readonly=True, index=True, copy=False)
    amount = fields.Integer(required=True, readonly=True, help="Amount in dong")
    payment_method_id = fields.Many2one("pos.payment.method", required=True, readonly=True, ondelete="restrict")
    session_id = fields.Many2one("pos.session", readonly=True)
    order_ref = fields.Char("POS order", readonly=True)
    state = fields.Selection(
        [("pending", "Waiting"), ("paid", "Paid"), ("cancelled", "Cancelled")],
        default="pending", required=True, readonly=True, index=True,
    )
    confirmed_manually = fields.Boolean(readonly=True, help="The cashier confirmed the payment without a bank notification.")
    confirmed_by_id = fields.Many2one("res.users", readonly=True)
    transaction_ids = fields.One2many("pos.vietqr.transaction", "request_id", readonly=True)

    _code_unique = models.Constraint("unique(code)", "The VietQR payment code must be unique.")

    @api.model
    def create_request(self, payment_method_id, amount, order_ref=None, session_id=None):
        """Called by the POS when the cashier sends a VietQR payment."""
        method = self.env["pos.payment.method"].browse(payment_method_id)
        if method.use_payment_terminal != "vietqr":
            raise UserError(_("This payment method does not use VietQR."))
        if amount <= 0 or amount != int(amount):
            raise UserError(_("VietQR can only collect a positive amount in whole dong."))
        code = CODE_PREFIX + "".join(secrets.choice(CODE_ALPHABET) for _ in range(7))
        request = self.create({
            "code": code,
            "amount": int(amount),
            "payment_method_id": method.id,
            "session_id": session_id,
            "order_ref": order_ref,
        })
        return {
            "id": request.id,
            "code": code,
            "amount": request.amount,
            "qr_payload": build_payload(method.vietqr_bank_bin, method.vietqr_account_number, request.amount, code),
            "bank_name": dict(method._fields["vietqr_bank_bin"].selection).get(method.vietqr_bank_bin),
            "account_number": method.vietqr_account_number,
            "account_name": method.vietqr_account_name or "",
        }

    def get_state(self):
        self.ensure_one()
        return self.state

    def cancel_request(self):
        self.filtered(lambda r: r.state == "pending").write({"state": "cancelled"})
        return True

    def confirm_manually(self):
        pending = self.filtered(lambda r: r.state == "pending")
        pending.write({"state": "paid", "confirmed_manually": True, "confirmed_by_id": self.env.uid})
        return bool(pending) or self.state == "paid"
