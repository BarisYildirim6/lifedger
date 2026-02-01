from datetime import datetime
import re

AMOUNT_REGEX = re.compile(r"(\d+[.,]\d{2})")
BLACKLIST = {"TOTAL", "KDV", "TUTAR", "FATURA"}
DATE_REGEX = re.compile(r"(\d{2}[./-]\d{2}[./-]\d{4})")
DATE_FORMATS = [
    "%d.%m.%Y",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%Y-%m-%d",
]

def extract_amount(text, confidences):
    matches = AMOUNT_REGEX.findall(text)
    if not matches:
        return None

    # Take highest numeric value (usually total)
    amount = max(float(m.replace(",", ".")) for m in matches)

    return {
        "value": amount,
        "confidence": 90
    }

def extract_merchant(lines):
    for line in lines[:5]:
        cleaned = line.strip().upper()
        if (
            len(cleaned) > 3 and
            cleaned.isupper() and
            cleaned not in BLACKLIST
        ):
            return {
                "value": cleaned.title(),
                "confidence": 70
            }

    return None

def extract_date(text):
    match = DATE_REGEX.search(text)
    if not match:
        return None

    raw = match.group(1)

    for fmt in DATE_FORMATS:
        try:
            parsed_date = datetime.strptime(raw, fmt).date()
            return {
                "value": parsed_date.isoformat(),
                "confidence": 85
            }
        except ValueError:
            continue

    return None

def parse_receipt_text(ocr):
    text = ocr["text"]
    lines = text.splitlines()
    ocr_confidence = ocr["avg_confidence"]

    amount = extract_amount(text, ocr["word_confidences"])
    merchant = extract_merchant(lines)
    date = extract_date(text)

    fields = [amount, merchant, date]
    valid = [f for f in fields if f]

    overall_conf = (
        sum(f["confidence"] for f in valid) / max(len(valid), 1)
    )

    return {
        "merchant": merchant,
        "amount": amount,
        "date": date,
        "ocr_confidence": ocr_confidence,
        "overall_confidence": round(overall_conf, 1),
    }
