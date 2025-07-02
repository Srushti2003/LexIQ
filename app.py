from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from transformers import PegasusForConditionalGeneration, PegasusTokenizer
import pdfplumber
import docx
import os
import requests
import urllib.parse
from typing import List
import re
import json
import openai
from collections import Counter, defaultdict
import matplotlib.pyplot as plt
import io
import base64
import matplotlib

app = Flask(__name__)
CORS(app)

model_name = "google/pegasus-xsum"
print("🔄 Loading summarization model...")
tokenizer = PegasusTokenizer.from_pretrained(model_name)
model = PegasusForConditionalGeneration.from_pretrained(model_name)
print("✅ Model loaded!")

API_TOKEN = "f37a1c77de92e97beb92f1d56b5307bd87670326"  # Replace with your token
BASE_URL = "https://api.indiankanoon.org"

# Utility to split text into chunks based on word count
def split_into_chunks(text, max_words=500):
    words = text.split()
    for i in range(0, len(words), max_words):
        yield " ".join(words[i:i + max_words])

# Summarize each chunk and combine
def summarize_text(text):
    if not text or len(text.strip()) == 0:
        raise ValueError("Input text is empty")

    summaries = []
    for chunk in split_into_chunks(text):
        inputs = tokenizer(chunk, return_tensors="pt", truncation=True, max_length=512)
        summary_ids = model.generate(
            **inputs, max_length=128, num_beams=4, early_stopping=True
        )
        summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        summaries.append(summary)

    return "\n\n".join(summaries)

# Extract text from uploaded file
def extract_text(file):
    if file.filename.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    elif file.filename.endswith(".docx"):
        doc = docx.Document(file)
        text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
    elif file.filename.endswith(".txt"):
        text = file.read().decode("utf-8", errors="ignore")
    else:
        return None

    text = text.strip()
    return text if text else None

def extract_sections_and_acts(text: str) -> List[str]:
    # Improved regex for Section/Act extraction
    section_patterns = [
        r"Section[s]?\s+(\d+[A-Z]?(?:,\s*\d+[A-Z]?)*)(?:\s+of)?\s*([A-Za-z\. ]*?(?:IPC|CrPC|Indian Penal Code|Code of Criminal Procedure|Evidence Act|Constitution of India))",
        r"Sec\.\s*(\d+[A-Z]?)\s*(?:of)?\s*([A-Za-z\. ]*?(?:IPC|CrPC|Indian Penal Code|Code of Criminal Procedure|Evidence Act|Constitution of India))",
        r"u/s\s*(\d+[A-Z]?)\s*([A-Za-z\. ]*?(?:IPC|CrPC|Indian Penal Code|Code of Criminal Procedure|Evidence Act|Constitution of India))"
    ]
    results = set()
    for pattern in section_patterns:
        for match in re.findall(pattern, text, re.IGNORECASE):
            section_nums = match[0]
            act = match[1].strip()
            # Handle multiple sections in one mention
            for sec in re.split(r",\s*", section_nums):
                if sec:
                    results.add(f"Section {sec} {act}")
    # Also extract standalone acts
    acts = re.findall(r"\b(IPC|CrPC|Indian Penal Code|Code of Criminal Procedure|Evidence Act|Constitution of India)\b", text, re.IGNORECASE)
    for a in acts:
        results.add(a.strip())
    return list(results)

@app.route("/")
def home():
    return render_template("index.html")

@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    query = data.get("query", "")
    if not query:
        return jsonify({"error": "No query provided"}), 400

    q_encoded = urllib.parse.quote_plus(query)
    url = f"{BASE_URL}/search/?formInput={q_encoded}&pagenum=0&maxpages=10"
    headers = {
        "Authorization": f"Token {API_TOKEN}",
        "Accept": "application/json"
    }

    res = requests.post(url, headers=headers)
    docs = res.json().get("docs", [])
    results = []

    for doc in docs:
        results.append({
            "title": doc.get("title"),
            "court": doc.get("docsource"),
            "date": doc.get("publishdate"),
            "doc_id": doc.get("tid")
        })

    return jsonify(results)

@app.route("/summarize-file", methods=["POST"])
def summarize_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    raw_text = extract_text(file)

    if not raw_text or len(raw_text.strip()) < 20:
        return jsonify({"error": "The file is empty or contains too little text."}), 400

    try:
        summary = summarize_text(raw_text)
        return jsonify({"summary": summary})
    except Exception as e:
        return jsonify({"error": f"Summarization failed: {str(e)}"}), 500

@app.route("/analyze-file", methods=["POST"])
def analyze_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    raw_text = extract_text(file)
    if not raw_text or len(raw_text.strip()) < 20:
        return jsonify({"error": "The file is empty or contains too little text."}), 400
    try:
        sections = extract_sections_and_acts(raw_text)
        return jsonify({"sections": sections})
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500

@app.route("/generate-arguments", methods=["POST"])
def generate_arguments():
    data = request.get_json()
    user_input = data.get("input", "").strip()
    if not user_input:
        return jsonify({"error": "No input provided."}), 400
    together_api_key = 'd474ca328e2468a8bab4337cdc91d384582516831bb21a93703024f051736795'  # <-- Put your Together.ai API key here
    if not together_api_key:
        return jsonify({"error": "Together.ai API key not set in code."}), 500
    import openai
    openai.api_key = together_api_key
    openai.api_base = "https://api.together.xyz/v1"
    model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
    prompt = f"Suggest multiple legal arguments or defenses for the following case facts or sections. Provide each argument as a separate bullet point.\n\n{user_input}\n\nArguments:"
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a legal assistant helping lawyers draft arguments."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=512,
            n=1,
            temperature=0.7
        )
        content = response["choices"][0]["message"]["content"]
        arguments = [arg.strip("- • ") for arg in content.split("\n") if arg.strip() and (arg.strip().startswith("-") or arg.strip().startswith("•") or arg.strip()[0].isdigit())]
        if not arguments:
            arguments = [content.strip()]
        return jsonify({"arguments": arguments})
    except Exception as e:
        return jsonify({"error": f"Together.ai argument generation failed: {str(e)}"}), 500

@app.route("/case-trends", methods=["POST"])
def case_trends():
    data = request.get_json()
    user_input = data.get("input", "").strip()
    if not user_input:
        return jsonify({"error": "No input provided."}), 400
    q_encoded = urllib.parse.quote_plus(user_input)
    url = f"{BASE_URL}/search/?formInput={q_encoded}&pagenum=0&maxpages=10"
    headers = {
        "Authorization": f"Token {API_TOKEN}",
        "Accept": "application/json"
    }
    try:
        res = requests.post(url, headers=headers)
        docs = res.json().get("docs", [])
        if not docs:
            return jsonify({"error": "No cases found for this section/law."})
        # Aggregate by year and court
        year_counts = Counter()
        court_counts = Counter()
        for doc in docs:
            year = str(doc.get("publishdate", "")).split("-")[0]
            if year.isdigit():
                year_counts[year] += 1
            court = doc.get("docsource", "Unknown Court")
            court_counts[court] += 1
        # Plot number of cases per year (aesthetic)
        matplotlib.use('Agg')
        plt.style.use('seaborn-v0_8-whitegrid')
        years = sorted(year_counts.keys())
        counts = [year_counts[y] for y in years]
        fig, ax = plt.subplots(figsize=(10, 5))
        bars = ax.bar(years, counts, color="#2980B9", edgecolor="#2C3E50", linewidth=1.5, zorder=3)
        ax.set_xlabel("Year", fontsize=14, fontweight='bold', color="#2C3E50")
        ax.set_ylabel("Number of Cases", fontsize=14, fontweight='bold', color="#2C3E50")
        ax.set_title(f"Number of Cases for '{user_input}' Over Years", fontsize=16, fontweight='bold', color="#2C3E50", pad=18)
        ax.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
        ax.set_axisbelow(True)
        ax.set_facecolor('#F4F1EA')
        fig.patch.set_facecolor('#F4F1EA')
        # Remove top/right spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        # Rounded bars and value labels
        for bar in bars:
            bar.set_linewidth(0)
            bar.set_alpha(0.92)
            bar.set_zorder(3)
            bar.set_capstyle('round') if hasattr(bar, 'set_capstyle') else None
            height = bar.get_height()
            ax.annotate(f'{height}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 6),
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=12, color="#2C3E50", fontweight='bold')
        # Rotate x-tick labels for years to prevent overlap
        plt.setp(ax.get_xticklabels(), rotation=30, ha='right', fontsize=12)
        plt.tight_layout(pad=2)
        # Save to static file
        img_path = os.path.join("static", "trend_chart.png")
        plt.savefig(img_path, dpi=160, bbox_inches='tight')
        plt.close(fig)
        image_url = "/static/trend_chart.png"
        return jsonify({"image_url": image_url})
    except Exception as e:
        return jsonify({"error": f"Trend analytics failed: {str(e)}"}), 500

def split_text_for_model(text, max_words=4000):
    words = text.split()
    for i in range(0, len(words), max_words):
        yield ' '.join(words[i:i+max_words])

@app.route("/client-brief", methods=["POST"])
def client_brief():
    text = request.form.get("text", "").strip() if "text" in request.form else ""
    file = request.files.get("file")
    raw_text = text
    if file:
        extracted = extract_text(file)
        if extracted:
            raw_text = (raw_text + "\n" + extracted).strip() if raw_text else extracted
    if not raw_text or len(raw_text.strip()) < 20:
        return jsonify({"error": "Please provide sufficient case details (text or file)."}), 400
    together_api_key = 'd474ca328e2468a8bab4337cdc91d384582516831bb21a93703024f051736795'  # <-- Your Together.ai API key
    import openai
    openai.api_key = together_api_key
    openai.api_base = "https://api.together.xyz/v1"
    model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
    # Step 1: Summarize each chunk
    chunk_summaries = []
    for chunk in split_text_for_model(raw_text, max_words=4000):
        prompt = f"Summarize the following case details in simple, layman's terms for a client. Make it short, clear, and easy to understand.\n\n{chunk}\n\nClient Brief:"
        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a legal assistant who explains legal matters simply to clients."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                n=1,
                temperature=0.6
            )
            content = response["choices"][0]["message"]["content"].strip()
            chunk_summaries.append(content)
        except Exception as e:
            return jsonify({"error": f"Client brief generation failed during chunking: {str(e)}"}), 500
    # Step 2: Combine and summarize again if needed
    combined = '\n'.join(chunk_summaries)
    if len(chunk_summaries) > 1:
        final_prompt = f"Combine and further simplify the following summaries into a single, short, client-friendly brief.\n\n{combined}\n\nClient Brief:"
        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a legal assistant who explains legal matters simply to clients."},
                    {"role": "user", "content": final_prompt}
                ],
                max_tokens=400,
                n=1,
                temperature=0.6
            )
            content = response["choices"][0]["message"]["content"].strip()
            return jsonify({"brief": content})
        except Exception as e:
            return jsonify({"error": f"Client brief generation failed during final summary: {str(e)}"}), 500
    else:
        return jsonify({"brief": chunk_summaries[0]})

if __name__ == "__main__":
    app.run(debug=True)