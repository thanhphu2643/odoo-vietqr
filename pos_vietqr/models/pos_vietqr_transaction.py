import json
import logging
import re

from odoo import fields, models

_logger = logging.getLogger(__name__)
CODE_PATTERN = re.compile(r"VQR[A-HJ-NP-Z2-9]{7}")


class PosVietqrTransaction(models.Model):
    """A bank notification received through the webhook, matched or not."""

    _name = "pos.vietqr.transaction"
    _description = "VietQR bank transaction"
    _order = "id desc"
    _rec_name = "provider_ref"

    provider = fields.Selection([("sepay", "SePay")], required=True, readonly=True)
    provider_ref = fields.Char("Provider reference", required=True, readonly=True, index=True)
    account_number = fields.Char(readonly=True)
    amount = fields.Integer(readonly=True)
    content = fields.Char("Transfer content", readonly=True)
    transaction_date = fields.Char(readonly=True)
    request_id = fields.Many2one("pos.vietqr.request", "Payment request", readonly=True, index=True)
    state = fields.Selection(
        [
            ("matched", "Matched"),
            ("unmatched", "No matching payment"),
            ("amount_mismatch", "Amount differs"),
        ],
        required=True, readonly=True, index=True,
    )
    raw = fields.Text("Raw notification", readonly=True)

    # The bank may notify the same transfer twice: it is recorded once.
    _provider_ref_unique = models.Constraint("unique(provider, provider_ref)", "This bank transaction was already received.")

    def _process_sepay(self, data):
        """Record one SePay notification and settle the payment request it refers to.

        Returns the transaction, or an empty recordset for notifications we ignore
        (outgoing transfers). A notification sent twice is recorded once.
        """
        if data.get("transferType") != "in":
            return self.browse()
        provider_ref = str(data.get("id") or "")
        if not provider_ref:
            raise ValueError("SePay notification without id")
        existing = self.search([("provider", "=", "sepay"), ("provider_ref", "=", provider_ref)], limit=1)
        if existing:
            return existing

        amount = int(data.get("transferAmount") or 0)
        account_number = str(data.get("accountNumber") or "")
        content = str(data.get("content") or "")
        request = self._find_request(content, data.get("code"), account_number)
        if not request:
            state = "unmatched"
        elif request.amount != amount:
            state = "amount_mismatch"
        else:
            state = "matched"
            request.write({"state": "paid"})

        _logger.info("VietQR: SePay transaction %s %s (%s)", provider_ref, state, request.code or "-")
        return self.create({
            "provider": "sepay",
            "provider_ref": provider_ref,
            "account_number": account_number,
            "amount": amount,
            "content": content[:255],
            "transaction_date": data.get("transactionDate"),
            "request_id": request.id,
            "state": state,
            "raw": json.dumps(data, ensure_ascii=False),
        })

    def _find_request(self, content, provider_code, account_number):
        # Banks may add prefixes, change case or drop spaces in the transfer content.
        haystack = f"{provider_code or ''} {content}".upper()
        codes = CODE_PATTERN.findall(haystack) or CODE_PATTERN.findall(haystack.replace(" ", ""))
        if not codes:
            return self.env["pos.vietqr.request"]
        domain = [("code", "in", codes), ("state", "=", "pending")]
        if account_number:
            domain.append(("payment_method_id.vietqr_account_number", "=", account_number))
        return self.env["pos.vietqr.request"].search(domain, limit=1)
