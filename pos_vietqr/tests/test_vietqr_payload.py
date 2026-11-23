from odoo.tests import BaseCase

from ..vietqr import build_payload, crc16_ccitt, parse_tlv


class TestVietqrPayload(BaseCase):
    def test_crc_matches_reference_vector(self):
        # Standard check value of CRC-16/CCITT-FALSE.
        self.assertEqual(crc16_ccitt(b"123456789"), 0x29B1)

    def test_payload_fields(self):
        payload = build_payload("970436", "0011001234567", 35000, "VQRABC2345")
        fields = parse_tlv(payload)
        self.assertEqual(fields["00"], "01")
        self.assertEqual(fields["01"], "12")
        self.assertEqual(fields["53"], "704")
        self.assertEqual(fields["54"], "35000")
        self.assertEqual(fields["58"], "VN")
        self.assertEqual(parse_tlv(fields["62"]), {"08": "VQRABC2345"})
        merchant = parse_tlv(fields["38"])
        self.assertEqual(merchant["00"], "A000000727")
        self.assertEqual(merchant["02"], "QRIBFTTA")
        self.assertEqual(parse_tlv(merchant["01"]), {"00": "970436", "01": "0011001234567"})
        self.assertTrue(payload.startswith("00020101021238570010A000000727"))
        self.assertEqual(int(fields["63"], 16), crc16_ccitt(payload[:-4].encode()))

    def test_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            build_payload("97043", "0011001234567", 1000, "X")  # BIN too short
        with self.assertRaises(ValueError):
            build_payload("970436", "0011-001", 1000, "X")  # account with a dash
        with self.assertRaises(ValueError):
            build_payload("970436", "0011001234567", 1000.5, "X")  # not whole dong
        with self.assertRaises(ValueError):
            build_payload("970436", "0011001234567", 0, "X")
        with self.assertRaises(ValueError):
            build_payload("970436", "0011001234567", 1000, "Cà phê")  # not ASCII
