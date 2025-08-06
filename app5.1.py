import os
import gradio as gr
from docx import Document
import fitz
import base64
import re
import html
from io import BytesIO
from rapidfuzz import fuzz
from datetime import datetime
from pygments import highlight
from pygments.lexers import PythonLexer, SqlLexer, JsonLexer, TextLexer
from pygments.formatters import HtmlFormatter
import time
from sentence_transformers import SentenceTransformer
import numpy as np

# === Ladda model för semantic search ===
model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

# === PDF/DOCX extraction ===
def extract_text_from_pdf(path):
    with fitz.open(path) as doc:
        return "\n".join(page.get_text() for page in doc)

def extract_text_from_docx(path):
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)

def load_documents(folder):
    docs = []
    for filename in os.listdir(folder):
        path = os.path.join(folder, filename)
        if filename.lower().endswith(".pdf"):
            content = extract_text_from_pdf(path)
        elif filename.lower().endswith(".docx"):
            content = extract_text_from_docx(path)
        else:
            continue
        embedding = model.encode(content)
        docs.append({"filename": filename, "content": content, "path": path, "embedding": embedding})
    return docs

documents = load_documents("docs")

# === Helper: extract snippet ===
def extract_context_snippet(text, query, max_chars=600):
    text = text.replace("\n", " ")
    match = re.search(re.escape(query), text, flags=re.IGNORECASE)
    if not match:
        return None
    start = max(match.start() - max_chars // 2, 0)
    end = min(match.end() + max_chars // 2, len(text))
    snippet = text[start:end]
    if start > 0:
        snippet = "…" + snippet
    if end < len(text):
        snippet += "…"
    def highlight_match(match):
        return f"<mark>{match.group(0)}</mark>"
    return re.sub(f"({re.escape(query)})", highlight_match, snippet, flags=re.IGNORECASE).strip()

# === search_documents med semantic + rapidfuzz ===
def search_documents(query, visible_count=5, sort_by="poäng", search_history=[]):
    start_time = time.time()

    if not query or len(query.strip()) < 2:
        html_history = "<br>".join(search_history)
        return "❗️ Skriv minst 2 tecken för att söka.", gr.update(visible=False), search_history, html_history

    query = query.strip()
    query_embedding = model.encode(query)
    results = []

    for doc in documents:
        filename_match = fuzz.partial_ratio(query.lower(), doc['filename'].lower()) > 80
        rapid_score = 60 if filename_match else 0
        rapid_score += 10 if fuzz.partial_ratio(query.lower(), doc['content'].lower()) > 80 else 0

        semantic_score = np.dot(query_embedding, doc['embedding']) / (np.linalg.norm(query_embedding) * np.linalg.norm(doc['embedding'])) * 100

        score = semantic_score * 0.8 + rapid_score * 0.2

        if score > 0:
            results.append((doc, score, filename_match))

    # Sortering
    if sort_by == "filnamn":
        results.sort(key=lambda x: x[0]['filename'])
    elif sort_by == "datum":
        results.sort(key=lambda x: os.stat(x[0]['path']).st_mtime, reverse=True)
    else:
        results.sort(key=lambda x: (x[1], x[2]), reverse=True)

    num_hits = len(results)
    num_docs = len(documents)
    elapsed = round(time.time() - start_time, 2)

    html_output = f"<p>🔎 {num_hits} träffar i {num_docs} genomsökta dokument. ⏱️ {elapsed} sekunder.</p>"

    # Sökhistorik
    if query not in search_history:
        search_history.append(query)
    if len(search_history) > 10:
        search_history.pop(0)
    html_history = "<br>".join(search_history)

    shown = 0
    for doc, score, filename_match in results:
        if shown >= visible_count:
            break

        ext = os.path.splitext(doc['filename'])[1].lower()
        icon = "📕" if ext == ".pdf" else "📄"

        stat = os.stat(doc['path'])
        modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d')
        size_mb = round(stat.st_size / (1024*1024), 2)

        highlighted_filename = re.sub(
            f"({re.escape(query)})",
            r"<mark>\1</mark>",
            doc['filename'],
            flags=re.IGNORECASE
        )

        snippet = extract_context_snippet(doc["content"], query)
        if not snippet and filename_match:
            snippet = f"<div style='color:green'><b>Sökordet hittades i filnamnet.</b></div>"

        html_output += f"<h4>{icon} {highlighted_filename}</h4>"
        html_output += f"<p>📅 Ändrad: {modified} | 💾 {size_mb} MB</p>"
        if snippet:
            html_output += f"<div style='background-color:#f6f6f6;padding:10px;border-radius:5px;margin-bottom:5px;'>{snippet}</div>"
        else:
            html_output += f"<p style='color:gray;'>⚠️ Ingen tydlig träfftext hittades.</p>"

        html_output += f"<p>🔍 <b>Matchningspoäng:</b> {round(score, 1)}</p><hr>"
        shown += 1

    show_more_visible = shown < len(results)
    return html_output if html_output else "❌ Inga träffar hittades.", gr.update(visible=show_more_visible), search_history, html_history

# === Gradio UI ===
with gr.Blocks() as demo:
    gr.Markdown("# 📚 NoWaste Dokumentbibliotek")

    dark_mode = gr.Checkbox(label="🌙 Dark mode", value=False)
    sort_dropdown = gr.Dropdown(label="🔽 Sortera efter", choices=["poäng", "filnamn", "datum"], value="poäng")
    search_history_box = gr.HTML(label="🕑 Sökhistorik")

    def toggle_dark_mode(is_dark):
        if is_dark:
            gr.themes.set_theme("dark")
        else:
            gr.themes.set_theme("default")

    dark_mode.change(fn=toggle_dark_mode, inputs=dark_mode, outputs=[])

    query1 = gr.Textbox(label="🔍 Sök i dokument", placeholder="Ex: inventering, pall, artikelnummer")
    output1 = gr.HTML()
    visible_count1 = gr.State(5)
    show_more_btn1 = gr.Button("⬇️ Visa fler", visible=False)
    search_history = gr.State([])

    def show_more_results(query, visible_count, sort_by, search_history):
        return search_documents(query, visible_count + 5, sort_by, search_history) + (visible_count + 5,)

    query1.change(
        fn=search_documents, 
        inputs=[query1, visible_count1, sort_dropdown, search_history], 
        outputs=[output1, show_more_btn1, search_history, search_history_box]
    )
    show_more_btn1.click(
        fn=show_more_results, 
        inputs=[query1, visible_count1, sort_dropdown, search_history], 
        outputs=[output1, show_more_btn1, visible_count1, search_history, search_history_box]
    )

if __name__ == "__main__":
    demo.launch()
