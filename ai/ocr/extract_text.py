import pytesseract
from pytesseract import Output
from PIL import Image
from pdf2image import convert_from_path

def extract_text_from_image(image_path, lang="eng"):
    image = Image.open(image_path)

    data = pytesseract.image_to_data(
        image,
        lang=lang,
        output_type=Output.DICT
    )

    words = []
    confidences = []

    for i, word in enumerate(data["text"]):
        conf = int(data["conf"][i])
        if word.strip() and conf > 0:
            words.append(word)
            confidences.append(conf)

    return {
        "text": " ".join(words),
        "avg_confidence": round(
            sum(confidences) / max(len(confidences), 1), 1
        ),
        "word_confidences": confidences,
    }

def extract_text_from_pdf(pdf_path, lang="eng"):
    pages = convert_from_path(pdf_path)

    full_text = []
    confidences = []

    for page in pages:
        data = pytesseract.image_to_data(
            page,
            lang=lang,
            output_type=Output.DICT
        )

        for i, word in enumerate(data["text"]):
            conf = int(data["conf"][i])
            if word.strip() and conf > 0:
                full_text.append(word)
                confidences.append(conf)

    return {
        "text": " ".join(full_text),
        "avg_confidence": round(
            sum(confidences) / max(len(confidences), 1), 1
        ),
        "word_confidences": confidences,
    }