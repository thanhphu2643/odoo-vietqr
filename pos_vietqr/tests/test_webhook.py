import json

from odoo.tests import HttpCase, tagged

URL = "/pos_vietqr/webhook/sepay"


@tagged("post_install", "-at_install")
class TestVietqrWebhook(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        journal = cls.env["account.journal"].search([("type", "=", "bank"), ("company_id", "=", cls.env.company.id)], limit=1)
        if not journal:
            cls.skipTest(cls, "needs a company with a chart of accounts (a Bank journal)")
        cls.method = cls.env["pos.payment.method"].create({
            "name": "VietQR",
            "journal_id": journal.id,
            "use_payment_terminal": "vietqr",
            "vietqr_bank_bin": "970436",
            "vietqr_account_number": "0011001234567",
            "vietqr_account_name": "NGUYEN VAN A",
        })
        cls.key = cls.method.vietqr_webhook_key
        cls.Request = cls.env["pos.vietqr.request"]
        cls.Transaction = cls.env["pos.vietqr.transaction"]

    def _new_request(self, amount=35000):
        info = self.Request.create_request(self.method.id, amount, "Shop/0001")
        return self.Request.browse(info["id"]), info

    def _notify(self, body, key=None):
        return self.url_open(
            URL,
            data=json.dumps(body),
            headers={"Content-Type": "application/json", "Authorization": f"Apikey {key or self.key}"},
        )

    def _sepay(self, ref, content, amount=35000, **extra):
        return {
            "id": ref, "gateway": "Vietcombank", "transactionDate": "2026-11-23 10:15:00",
            "accountNumber": "0011001234567", "code": None, "content": content,
            "transferType": "in", "transferAmount": amount, "accumulated": 0,
            "referenceCode": "FT26327", "description": content, **extra,
        }

    def test_create_request_returns_scannable_payload(self):
        request, info = self._new_request()
        self.assertRegex(info["code"], r"^VQR[A-HJ-NP-Z2-9]{7}$")
        self.assertIn(info["code"], info["qr_payload"])
        self.assertEqual(info["bank_name"], "Vietcombank")
        self.assertEqual(request.state, "pending")

    def test_matching_transfer_marks_request_paid(self):
        request, info = self._new_request()
        # Banks often prepend text and lowercase the content.
        response = self._notify(self._sepay(9001, f"MBVCB.123 {info['code'].lower()} chuyen tien"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True})
        self.assertEqual(request.state, "paid")
        self.assertEqual(request.transaction_ids.state, "matched")

    def test_duplicate_notification_is_recorded_once(self):
        request, info = self._new_request()
        self._notify(self._sepay(9002, info["code"]))
        self._notify(self._sepay(9002, info["code"]))
        self.assertEqual(self.Transaction.search_count([("provider_ref", "=", "9002")]), 1)

    def test_wrong_amount_keeps_request_waiting(self):
        request, info = self._new_request(35000)
        self._notify(self._sepay(9003, info["code"], amount=30000))
        self.assertEqual(request.state, "pending")
        self.assertEqual(request.transaction_ids.state, "amount_mismatch")

    def test_unknown_content_is_kept_for_review(self):
        self._notify(self._sepay(9004, "tra tien hang"))
        transaction = self.Transaction.search([("provider_ref", "=", "9004")])
        self.assertEqual(transaction.state, "unmatched")

    def test_other_account_does_not_settle(self):
        request, info = self._new_request()
        self._notify(self._sepay(9005, info["code"], accountNumber="999999999"))
        self.assertEqual(request.state, "pending")

    def test_outgoing_transfer_is_ignored(self):
        request, info = self._new_request()
        self._notify(self._sepay(9006, info["code"], transferType="out"))
        self.assertEqual(request.state, "pending")
        self.assertFalse(self.Transaction.search([("provider_ref", "=", "9006")]))

    def test_wrong_key_is_rejected(self):
        request, info = self._new_request()
        response = self._notify(self._sepay(9007, info["code"]), key="not-the-key")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(request.state, "pending")

    def test_cancelled_request_is_not_paid_later(self):
        request, info = self._new_request()
        request.cancel_request()
        self._notify(self._sepay(9008, info["code"]))
        self.assertEqual(request.state, "cancelled")
        self.assertEqual(self.Transaction.search([("provider_ref", "=", "9008")]).state, "unmatched")

    def test_manual_confirmation_is_recorded(self):
        request, _info = self._new_request()
        self.assertTrue(request.confirm_manually())
        self.assertEqual(request.state, "paid")
        self.assertTrue(request.confirmed_manually)
        self.assertEqual(request.confirmed_by_id, self.env.user)

    def test_requires_bank_journal(self):
        cash = self.env["account.journal"].search([("type", "=", "cash"), ("company_id", "=", self.env.company.id)], limit=1)
        with self.assertRaises(Exception):
            self.method.journal_id = cash

    def test_rejects_amount_that_vietqr_cannot_collect(self):
        with self.assertRaises(Exception):
            self.Request.create_request(self.method.id, -1000)
        with self.assertRaises(Exception):
            self.Request.create_request(self.method.id, 1000.5)
