# POS VietQR for Odoo

Odoo 19 Point of Sale module that shows a VietQR code for the order total and marks the
payment as paid by itself when the money reaches your bank account.

```
Cashier picks VietQR → POS shows a QR with the amount and a payment code (VQR…)
Customer scans it in any Vietnamese banking app and transfers
SePay sees the transfer → calls Odoo's webhook → POS turns green and validates the order
```

No more checking the banking app before handing over the order. If the notification is
late, the cashier can still confirm by hand, and Odoo records who did.

## Features

- Dynamic VietQR (NAPAS 247, EMVCo) with the exact amount and a unique transfer content,
  generated on the server and tested against the CRC reference vector.
- Automatic confirmation from SePay bank notifications, matched on the payment code,
  the amount and the receiving account. Banks that rewrite the content (prefixes,
  lowercase, dropped spaces) still match.
- Safe by default: a transfer with a different amount, for a cancelled payment or with an
  unknown content never settles anything; it lands in **VietQR bank transactions** for review.
  Repeated notifications are recorded once. The webhook rejects calls without the API key.
- Every POS payment keeps its VietQR code (`transaction_id`) for reconciliation.

## Setup

1. Install **POS VietQR** (`pos_vietqr`, depends on `point_of_sale`).
2. *Point of Sale → Configuration → Payment Methods → New*: pick a **Bank** journal, set
   *Use a Payment Terminal* to **VietQR**, then the bank, account number and holder name.
   Add the method to your POS.
3. In [SePay](https://sepay.vn), link the same bank account and add a webhook:
   - URL: the **Webhook URL** shown on the payment method
     (`https://<your-odoo>/pos_vietqr/webhook/sepay`). Odoo must be reachable from the
     internet over HTTPS.
   - Authentication: **API Key**, using the **Webhook API key** shown on the payment method.

The bank list holds the 20 most used banks. Before going live, scan a QR from the POS with
your own banking app and check that it shows your account and the right amount.

## Try the webhook without a bank

```sh
curl -X POST https://<your-odoo>/pos_vietqr/webhook/sepay \
  -H "Authorization: Apikey <webhook key>" -H "Content-Type: application/json" \
  -d '{"id": 1, "transferType": "in", "transferAmount": 35000,
       "accountNumber": "<your account>", "content": "<VQR code shown in the POS>"}'
```

## Tests

```sh
odoo -d <db> -i pos_vietqr --test-enable --test-tags /pos_vietqr --stop-after-init
```

The webhook tests need a company with a chart of accounts (a Bank journal).

## License

LGPL-3
