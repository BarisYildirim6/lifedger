from .extract_text import extract_text_from_image, extract_text_from_pdf
from .ocr_confidence import parse_receipt_text
from pdf2image.exceptions import PDFInfoNotInstalledError
from pytesseract import TesseractNotFoundError

def scan_file(path):
    try:
        if path.lower().endswith(".pdf"):
            ocr_result  = extract_text_from_pdf(path)
        else:
            ocr_result  = extract_text_from_image(path)

        return parse_receipt_text(ocr_result)
    except PDFInfoNotInstalledError:
        return {
            "error": "PDF scanning is temporarily unavailable. Please upload an image instead."
        }
    except TesseractNotFoundError:
        return {
            "error": "OCR engine is not installed. Please contact the administrator."
        }