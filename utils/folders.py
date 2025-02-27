import pdfplumber
from langchain.text_splitter import RecursiveCharacterTextSplitter
import pytesseract
from pdf2image import convert_from_path
import subprocess
from dotenv import load_dotenv
import requests
import os, re
import chardet
import spacy


# Load NLP model for keyword extraction
nlp = spacy.load("en_core_web_sm")
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def extract_keywords(text):
    """Extracts relevant keywords dynamically using NLP."""
    doc = nlp(text)
    return {token.lemma_.lower() for token in doc if token.pos_ in {"NOUN", "VERB"} and len(token.text) > 2}


def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file using pdfplumber, with OCR fallback for scanned pages."""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
            else:
                # Convert scanned page to image and extract text using OCR
                image = convert_from_path(pdf_path, first_page=page.page_number, last_page=page.page_number)[0]
                text += pytesseract.image_to_string(image)

    return text.strip()


def extract_text_from_doc(doc_path):
    """Extracts text from a DOC (old Word 97-2003 format) file using catdoc."""
    try:
        result = subprocess.run(["catdoc", doc_path], capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        print(f"Error extracting text from {doc_path}: {e}")
        return ""


def call_gemini(prompt):
    """Calls the Gemini API with the given prompt."""
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    
    headers = {
        "Content-Type": "application/json",
    }
    
    params = {
        "key": GEMINI_API_KEY
    }
    
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    response = requests.post(url, headers=headers, json=data, params=params)

    if response.status_code == 200:
        return response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response")
    else:
        return f"Error: {response.status_code} - {response.text}"
    
    
def summarize_text(text):
    """Summarizes the text using Gemini before passing it to the main query."""
    summary_prompt = f"Summarize this document in 3-5 sentences:\n\n{text[:5000]}"  # Truncate long text
    return call_gemini(summary_prompt)


def detect_encoding(file_path):
    """Detects the encoding of a file by reading a small portion."""
    with open(file_path, "rb") as f:
        raw_data = f.read(1024)
        return chardet.detect(raw_data)["encoding"]


def extract_dates(text):
    """Extracts potential dates from the document text."""
    date_patterns = [
        r"\b\d{1,2}/\d{1,2}/\d{4}\b",  # MM/DD/YYYY or DD/MM/YYYY
        r"\b\d{4}-\d{2}-\d{2}\b",      # YYYY-MM-DD
        r"\b\d{1,2} [A-Za-z]+ \d{4}\b" # 12 March 2024, 5 June 2023
    ]

    possible_dates = []
    for pattern in date_patterns:
        possible_dates.extend(re.findall(pattern, text))

    return possible_dates
