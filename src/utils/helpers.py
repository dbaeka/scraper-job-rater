import os

import yaml
from PyPDF2 import PdfReader


def extract_resume_text(dir):
    files = os.listdir(dir)
    pdf_files = [f for f in files if f.endswith('.pdf')]
    resume_text = []
    for pdf_file in pdf_files:
        reader = PdfReader(os.path.join(dir, pdf_file))
        for page in reader.pages:
            text = page.extract_text()
            if text:
                resume_text.append(text)
    return "\n".join(resume_text)


def get_config(config_path="app.yaml"):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)
