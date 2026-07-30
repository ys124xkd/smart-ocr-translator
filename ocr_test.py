import gradio as gr
import pytesseract
from PIL import Image, ImageDraw
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from deep_translator import GoogleTranslator

# =========================
# PATH TESSERACT
# =========================
pytesseract.pytesseract.tesseract_cmd = r"C:/Program Files/Tesseract-OCR/tesseract.exe"

# =========================
# OCR + BOUNDING BOX
# =========================
def ocr_with_boxes(image):
    if image is None:
        return "No image uploaded", None

    try:
        if isinstance(image, np.ndarray):
            img = Image.fromarray(image)
        else:
            img = image

        draw = ImageDraw.Draw(img)

        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

        n_boxes = len(data['text'])

        # Simpan per baris (paragraf)
        lines = {}

        for i in range(n_boxes):
            text = data['text'][i]

            try:
                conf = float(data['conf'][i])
            except:
                conf = -1

            if conf > 50 and text.strip() != "":
                block_num = data['block_num'][i]
                line_num = data['line_num'][i]

                key = (block_num, line_num)

                if key not in lines:
                    lines[key] = {
                        "words": [],
                        "boxes": []
                    }

                lines[key]["words"].append(text)

                x, y, w, h = (
                    data['left'][i],
                    data['top'][i],
                    data['width'][i],
                    data['height'][i]
                )

                lines[key]["boxes"].append((x, y, w, h))

        # Susun paragraf berdasarkan posisi (atas ke bawah)
        sorted_lines = sorted(lines.items(), key=lambda x: x[1]["boxes"][0][1])

        final_text = ""
        for _, line_data in sorted_lines:
            line_text = " ".join(line_data["words"])
            final_text += line_text + "\n"

            # gambar bounding box per kata
            for (x, y, w, h) in line_data["boxes"]:
                draw.rectangle(
                    [(x, y), (x + w, y + h)],
                    outline="red",
                    width=2
                )

        return final_text.strip(), img

    except Exception as e:
        return f"Error OCR: {str(e)}", None


# =========================
# TRANSLATION FUNCTION
# =========================
def translate_text(text):
    if not text:
        return ""

    try:
        # Deteksi sederhana:
        # Jika banyak huruf Indonesia → translate ke Inggris
        # Default: Inggris → Indonesia

        translator_id = GoogleTranslator(source='en', target='id')
        translator_en = GoogleTranslator(source='id', target='en')

        # Coba deteksi bahasa sederhana
        if any(word in text.lower() for word in ["dan", "yang", "di", "ke", "dengan"]):
            # Indonesia → Inggris
            translated = translator_en.translate(text)
        else:
            # Inggris → Indonesia
            translated = translator_id.translate(text)

        return translated

    except Exception as e:
        return f"Translation error: {str(e)}"


# =========================
# SAVE PDF
# =========================
def save_to_pdf(text, filename="output.pdf"):
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    lines = text.split("\n")
    y = height - 40

    for line in lines:
        wrapped_lines = [line[i:i+90] for i in range(0, len(line), 90)]

        for wl in wrapped_lines:
            c.drawString(40, y, wl)
            y -= 15

            if y < 40:
                c.showPage()
                y = height - 40

    c.save()
    return filename


# =========================
# PIPELINE
# =========================
def process(image):
    text, boxed_image = ocr_with_boxes(image)

    if boxed_image is None:
        return text, None, None, None

    translated_text = translate_text(text)
    pdf_path = save_to_pdf(text)

    return text, translated_text, boxed_image, pdf_path


# =========================
# GRADIO UI
# =========================
with gr.Blocks() as app:
    gr.Markdown("## 📄 OCR + Bounding Box + Translate + PDF")

    with gr.Row():
        input_img = gr.Image(type="numpy", label="Upload Image")

    with gr.Row():
        btn = gr.Button("Process OCR")

    with gr.Row():
        output_text = gr.Textbox(label="Extracted Text", lines=10)
        output_translate = gr.Textbox(label="Translated Text", lines=10)

    with gr.Row():
        output_img = gr.Image(label="Image with Bounding Box")
        output_pdf = gr.File(label="Download PDF")

    btn.click(
        fn=process,
        inputs=input_img,
        outputs=[output_text, output_translate, output_img, output_pdf]
    )

app.launch()