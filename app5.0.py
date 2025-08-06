# === IDENTISK TILL VERSION A ===
# Men ta bort:
# - sentence-transformers import
# - embeddings-kod
# - semantic scoring

# === ERSÄTT FUNKTION search_documents med: ===

def search_documents(query, visible_count=5, sort_by="poäng", search_history=[]):
    start_time = time.time()

    if not query or len(query.strip()) < 2:
        return "❗️ Skriv minst 2 tecken för att söka.", gr.update(visible=False), search_history

    query = query.strip()
    results = []

    for doc in documents:
        filename_match = fuzz.partial_ratio(query.lower(), doc['filename'].lower()) > 80
        content_match = fuzz.partial_ratio(query.lower(), doc['content'].lower()) > 80

        score = 0
        if filename_match:
            score += 60
        if content_match:
            score += 10

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

    if query not in search_history:
        search_history.append(query)
    if len(search_history) > 10:
        search_history.pop(0)

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
    return html_output if html_output else "❌ Inga träffar hittades.", gr.update(visible=show_more_visible), search_history
