odoo.define('pos_vietqr.VietQRPopup', function (require) {
'use strict';

const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
const Registries = require('point_of_sale.Registries');
const { onMounted, onWillUnmount, useState } = owl;

const POLL_MS = 2000;

// Shows the QR code and waits for the bank notification (via the webhook) to mark the
// request paid. The cashier can still confirm by hand after checking the bank app.
class VietQRPopup extends AbstractAwaitablePopup {
    setup() {
        super.setup();
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
        return this.env.pos.format_currency(this.props.request.amount);
    }

    async poll() {
        if (this.busy || this.state.paid) {
            return;
        }
        this.busy = true;
        try {
            const state = await this.rpc(
                { model: 'pos.vietqr.request', method: 'get_state', args: [[this.props.request.id]] },
                { shadow: true }
            );
            if (state === 'paid') {
                this.markPaid();
            } else if (state === 'cancelled') {
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
        setTimeout(() => this.confirm(), 900);
    }

    async confirmManually() {
        this.state.confirming = true;
        try {
            const ok = await this.rpc({ model: 'pos.vietqr.request', method: 'confirm_manually', args: [[this.props.request.id]] });
            if (ok) {
                this.markPaid();
            }
        } finally {
            this.state.confirming = false;
        }
    }
}
VietQRPopup.template = 'pos_vietqr.VietQRPopup';

Registries.Component.add(VietQRPopup);

return VietQRPopup;
});
