import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

const POLL_MS = 2000;

// Shows the QR code and asks the server every few seconds whether the bank notification
// (SePay webhook) has marked the request paid. The cashier can also confirm by hand.
export class VietQRDialog extends Component {
    static template = "pos_vietqr.VietQRDialog";
    static components = { Dialog };
    static props = ["request", "getPayload", "close"];

    setup() {
        this.orm = useService("orm");
        this.state = useState({ paid: false, confirming: false });
        onMounted(() => {
            this.timer = setInterval(() => this.poll(), POLL_MS);
        });
        onWillUnmount(() => clearInterval(this.timer));
    }

    get qrUrl() {
        const value = encodeURIComponent(this.props.request.qr_payload);
        return `/report/barcode/?barcode_type=QR&value=${value}&width=320&height=320`;
    }

    get amount() {
        return this.env.utils.formatCurrency(this.props.request.amount);
    }

    async poll() {
        if (this.busy || this.state.paid) {
            return;
        }
        this.busy = true;
        try {
            const state = await this.orm.silent.call("pos.vietqr.request", "get_state", [[this.props.request.id]]);
            if (state === "paid") {
                this.markPaid();
            } else if (state === "cancelled") {
                this.cancel();
            }
        } catch {
            // Offline or server busy: keep showing the code and try again on the next tick.
        } finally {
            this.busy = false;
        }
    }

    markPaid() {
        clearInterval(this.timer);
        this.state.paid = true;
        setTimeout(() => {
            this.props.getPayload(true);
            this.props.close();
        }, 900);
    }

    async confirmManually() {
        this.state.confirming = true;
        try {
            if (await this.orm.call("pos.vietqr.request", "confirm_manually", [[this.props.request.id]])) {
                this.markPaid();
            }
        } finally {
            this.state.confirming = false;
        }
    }

    cancel() {
        clearInterval(this.timer);
        this.props.getPayload(false);
        this.props.close();
    }
}
