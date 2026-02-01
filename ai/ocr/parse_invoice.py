import re
from datetime import datetime

AMOUNT_REGEX = re.compile(r'(\d+[.,]\d{2})')
DATE_REGEX = re.compile(
    r'(\d{2}[./-]\d{2}[./-]\d{4})'
)

def parse_invoice_text(text):
    amounts = AMOUNT_REGEX.findall(text)
    dates = DATE_REGEX.findall(text)

    amount = max(
        [float(a.replace(",", ".")) for a in amounts],
        default=None
    )

    parsed_date = None
    if dates:
        try:
            parsed_date = datetime.strptime(
                dates[0], "%d.%m.%Y"
            ).date()
        except ValueError:
            pass

    merchant = text.split("\n")[0][:100]

    return {
        "amount": amount,
        "date": parsed_date,
        "merchant": merchant.strip(),
        "raw_text": text[:2000],
    }