import hmac
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class VietqrWebhook(http.Controller):
    @http.route("/pos_vietqr/webhook/sepay", type="http", auth="public", methods=["POST"], csrf=False)
    def sepay(self, **_kwargs):
        if not self._authorized(request.httprequest.headers.get("Authorization", "")):
            return self._reply(401, {"success": False, "error": "unauthorized"})
        try:
            data = json.loads(request.httprequest.get_data() or b"{}")
        except ValueError:
            return self._reply(400, {"success": False, "error": "invalid json"})
        try:
            request.env["pos.vietqr.transaction"].sudo()._process_sepay(data)
        except ValueError as error:
            return self._reply(400, {"success": False, "error": str(error)})
        return self._reply(200, {"success": True})

    def _authorized(self, header):
        scheme, _, key = header.partition(" ")
        if scheme.lower() != "apikey" or not key:
            return False
        methods = request.env["pos.payment.method"].sudo().search([("use_payment_terminal", "=", "vietqr")])
        return any(m.vietqr_webhook_key and hmac.compare_digest(m.vietqr_webhook_key, key.strip()) for m in methods)

    def _reply(self, status, body):
        return request.make_json_response(body, status=status)
