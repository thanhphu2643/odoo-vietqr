odoo.define('pos_vietqr.payment', function (require) {
'use strict';

const core = require('web.core');
const rpc = require('web.rpc');
const models = require('point_of_sale.models');
const PaymentInterface = require('point_of_sale.PaymentInterface');
const { Gui } = require('point_of_sale.Gui');

const _t = core._t;

const PaymentVietQR = PaymentInterface.extend({
    send_payment_request: async function (cid) {
        await this._super(...arguments);
        const order = this.pos.get_order();
        const line = order.get_paymentline(cid);
        let request;
        try {
            request = await rpc.query({
                model: 'pos.vietqr.request',
                method: 'create_request',
                args: [this.payment_method.id, line.amount, order.name, this.pos.pos_session.id],
            });
        } catch (error) {
            const message = (error.message && error.message.data && error.message.data.message) || _t('Check the connection to Odoo and try again.');
            Gui.showPopup('ErrorPopup', { title: _t('VietQR payment could not start'), body: message });
            return false;
        }
        this.request = request;
        const { confirmed } = await Gui.showPopup('VietQRPopup', { request });
        this.request = null;
        if (!confirmed) {
            await this._cancel(request.id);
            return false;
        }
        line.transaction_id = request.code;
        return true;
    },

    send_payment_cancel: async function (order, cid) {
        await this._super(...arguments);
        if (this.request) {
            await this._cancel(this.request.id);
        }
        return true;
    },

    _cancel: function (requestId) {
        return rpc.query({ model: 'pos.vietqr.request', method: 'cancel_request', args: [[requestId]] }).catch(() => {});
    },
});

models.register_payment_method('vietqr', PaymentVietQR);

return PaymentVietQR;
});
