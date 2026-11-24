import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { VietQRDialog } from "./vietqr_dialog";

// The QR code is shown in a dialog that waits for the bank notification (or the cashier's
// confirmation). The payment line is done when the dialog says the money arrived.
export class PaymentVietQR extends PaymentInterface {
    async send_payment_request(uuid) {
        await super.send_payment_request(...arguments);
        const order = this.pos.get_order();
        const line = order.payment_ids.find((paymentLine) => paymentLine.uuid === uuid);
        let request;
        try {
            request = await this.env.services.orm.call("pos.vietqr.request", "create_request", [
                this.payment_method_id.id,
                line.amount,
                order.pos_reference || order.name || "",
                this.pos.session.id,
            ]);
        } catch (error) {
            this.env.services.dialog.add(AlertDialog, {
                title: _t("VietQR payment could not start"),
                body: error.data?.message || _t("Check the connection to Odoo and try again."),
            });
            return false;
        }
        this.request = request;
        const paid = await makeAwaitable(this.env.services.dialog, VietQRDialog, { request });
        this.request = null;
        if (!paid) {
            await this._cancel(request.id);
            return false;
        }
        line.transaction_id = request.code;
        return true;
    }

    async send_payment_cancel(order, uuid) {
        await super.send_payment_cancel(...arguments);
        if (this.request) {
            await this._cancel(this.request.id);
        }
        return true;
    }

    _cancel(requestId) {
        return this.env.services.orm.silent
            .call("pos.vietqr.request", "cancel_request", [[requestId]])
            .catch(() => {});
    }
}

register_payment_method("vietqr", PaymentVietQR);
