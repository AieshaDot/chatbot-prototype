import fitz  # PyMuPDF
import docx
import pandas as pd

def extract_text_from_pdf(file_path):
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text


def extract_text_from_xlsx(path):
    df_list = pd.read_excel(path, sheet_name=None)  # All sheets
    all_text = []
    for sheet, df in df_list.items():
        all_text.append(f"Sheet: {sheet}")
        all_text.append(df.astype(str).to_string(index=False))
    return "\n".join(all_text)