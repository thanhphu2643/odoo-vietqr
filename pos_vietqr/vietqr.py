"""VietQR payload builder (NAPAS 247 transfer QR on top of EMVCo Merchant Presented Mode)."""

import re

NAPAS_GUID = "A000000727"
SERVICE_TO_ACCOUNT = "QRIBFTTA"
_SAFE_TEXT = re.compile(r"^[A-Za-z0-9 ]*$")


def _tlv(tag, value):
    if len(value) > 99:
        raise ValueError(f"VietQR field {tag} is too long")
    return f"{tag}{len(value):02d}{value}"


def crc16_ccitt(data):
    """CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF), as EMVCo requires."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else crc << 1
            crc &= 0xFFFF
    return crc


def build_payload(bank_bin, account_number, amount, message):
    """Return the string to encode in the QR code.

    amount is in VND (whole dong); message is the transfer description the payer's
    bank pre-fills, kept to ASCII letters, digits and spaces so banks pass it on unchanged.
    """
    if not re.fullmatch(r"\d{6}", bank_bin or ""):
        raise ValueError("The bank BIN must be 6 digits")
    if not re.fullmatch(r"[A-Za-z0-9]{1,19}", account_number or ""):
        raise ValueError("The account number must be 1 to 19 letters or digits")
    if amount <= 0 or amount != int(amount):
        raise ValueError("The amount must be a positive whole number of dong")
    if not _SAFE_TEXT.match(message) or len(message) > 25:
        raise ValueError("The message must be at most 25 letters, digits or spaces")

    beneficiary = _tlv("00", bank_bin) + _tlv("01", account_number)
    merchant = _tlv("00", NAPAS_GUID) + _tlv("01", beneficiary) + _tlv("02", SERVICE_TO_ACCOUNT)
    payload = (
        _tlv("00", "01")  # payload format indicator
        + _tlv("01", "12")  # dynamic QR: amount is fixed for this payment
        + _tlv("38", merchant)
        + _tlv("53", "704")  # VND
        + _tlv("54", str(int(amount)))
        + _tlv("58", "VN")
        + _tlv("62", _tlv("08", message))  # purpose of transaction
        + "6304"
    )
    return payload + f"{crc16_ccitt(payload.encode('ascii')):04X}"


def parse_tlv(payload):
    """Split a payload into {tag: value} (one level). Used by tests and for debugging."""
    fields, index = {}, 0
    while index < len(payload):
        tag, length = payload[index:index + 2], int(payload[index + 2:index + 4])
        fields[tag] = payload[index + 4:index + 4 + length]
        index += 4 + length
    return fields
