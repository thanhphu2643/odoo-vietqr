{
    "name": "POS VietQR",
    "summary": "Show a VietQR code in the Point of Sale and confirm the payment automatically when the money arrives",
    "version": "19.0.1.0.0",
    "category": "Sales/Point of Sale",
    "author": "Nguyen Thanh Phu",
    "website": "https://github.com/thanhphu2643",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "data": [
        "security/ir.model.access.csv",
        "views/pos_payment_method_views.xml",
        "views/pos_vietqr_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_vietqr/static/src/**/*",
        ],
    },
    "images": ["static/description/banner.png"],
    "installable": True,
}
