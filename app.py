import argparse
import os
import re
import sqlite3
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify
import requests
import numpy as np
from sentence_transformers import SentenceTransformer
import xcommand
DEFAULT_MODEL = r"C:\Users\umair\Desktop\Langraph\AraGemma-Embedding-300m"
DEFAULT_DB    = r"C:\Users\umair\Desktop\Langraph\embeddings.db"
DEFAULT_DLL   = r"C:\Users\umair\Desktop\Langraph\sqlite-vec\vec0.dll"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "gemma3:4b"   
def expand_urdu_query(q: str):
    synonyms = [
        "حبسِ جسم", "ہیبیس کارپس",
        "غیر قانونی گرفتاری", "غیر قانونی حراست",
        "گرفتاری", "حراست", "وارنٹ",
        "آئینی درخواست", "ہائی کورٹ", "عدالت", "ضمانت"
    ]
    terms = set([q.strip()] + synonyms)
    return list(terms)

# ---------- DB / vec0 ----------
def connect_db(db_path: str, dll_path: str) -> sqlite3.Connection:
    con = sqlite3.connect(db_path, check_same_thread=False)
    con.enable_load_extension(True)
    con.load_extension(dll_path)
    con.execute("PRAGMA foreign_keys = ON;")
    return con

def hybrid_search(con, model, query: str, top_k=4, fts_k=100):
    # FTS prefilter (BM25)
    try:
        terms = expand_urdu_query(query)
        fts_expr = " OR ".join([f'"{t}"' for t in terms])
        rows = con.execute("""
            SELECT rowid
            FROM chunks_fts
            WHERE chunks_fts MATCH ?
            ORDER BY bm25(chunks_fts) ASC
            LIMIT ?;""", (fts_expr, fts_k)).fetchall()
        candidate_ids = [r[0] for r in rows]
    except sqlite3.OperationalError:
        candidate_ids = []

    q = model.encode([query], normalize_embeddings=True, convert_to_numpy=True).astype("float32")[0]

    if candidate_ids:
        placeholders = ",".join("?" * len(candidate_ids))
        rows = con.execute(f"""
            SELECT v.rowid, v.distance
            FROM vectors v
            WHERE v.rowid IN ({placeholders})
              AND v.embedding MATCH ?
            ORDER BY v.distance
            LIMIT ?;""", (*candidate_ids, q.tobytes(), min(top_k * 5, fts_k))).fetchall()
    else:
        rows = con.execute("""
            SELECT rowid, distance FROM vectors
            WHERE embedding MATCH ? ORDER BY distance LIMIT ?;""",
            (q.tobytes(), top_k * 5)).fetchall()

    # tiny keyword bonus to break ties
    keywords = ["حبسِ جسم", "ہیبیس کارپس", "گرفتاری", "حراست", "وارنٹ"]
    scored = []
    for rowid, dist in rows:
        txt = con.execute("SELECT text FROM chunks WHERE id=?", (rowid,)).fetchone()[0]
        cosine = 1 - (dist * dist) / 2.0
        bonus = sum(1 for k in keywords if k in txt) * 0.1
        scored.append((cosine + bonus, txt))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [t for _, t in scored[:top_k]]
    return top

def build_prompt(context_chunks, user_query):
    ctx = "\n\n---\n\n".join(context_chunks)
    prompt = f"""آپ ایک مختصر قانونی مددگار ہیں۔
سوال اردو میں ہوگا۔ آپ کا جواب سادہ، مختصر (۲–۳ جملے) اور واضح ہونا چاہیے۔
اگر مواد کافی نہ ہو تو مختصراً بتائیں کہ معلومات دستیاب نہیں۔

سوال:
{user_query}

حوالہ متن (صرف سمجھنے کیلئے، حوالہ نہ دیں):
{ctx}

جواب اردو میں ۲–۳ جملوں میں، سادہ زبان میں دیں:"""
    return prompt

def call_ollama(ollama_url, model_name, prompt):
    url = f"{ollama_url}/api/generate"
    payload = {"model": model_name, "prompt": prompt, "stream": False}
    r = requests.post(url, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    return data.get("response", "").strip()

# ---------- Flask ----------
app = Flask(__name__)

# No HTML global anymore; delegate to xcommand
@app.route("/", methods=["GET"])
def index():
    return render_template_string(xcommand.UI_HTML)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    user_query = (data.get("message") or "").strip()
    if not user_query:
        return jsonify({"answer": "براہِ کرم سوال لکھیں۔"})

    try:
        contexts = hybrid_search(DB_CON, EMBED_MODEL, user_query, top_k=4, fts_k=120)
        prompt = build_prompt(contexts if contexts else ["(کوئی متعلقہ متن نہیں ملا)"], user_query)

        try:
            answer = call_ollama(OLLAMA_URL, OLLAMA_MODEL, prompt)
            answer = "\n".join(answer.splitlines()).strip()
        except Exception:
            best = contexts[0] if contexts else "معاف کیجئے، ابھی جواب دستیاب نہیں۔"
            answer = best[:450] + ("..." if len(best) > 450 else "")

        return jsonify({"answer": answer})
    except Exception:
        return jsonify({"answer": "ایک خرابی پیش آگئی۔"}), 500

def boot(model_path, db_path, dll_path, ollama_url, ollama_model, host, port, debug):
    global DB_CON, EMBED_MODEL, OLLAMA_URL, OLLAMA_MODEL
    EMBED_MODEL = SentenceTransformer(model_path)
    DB_CON = connect_db(db_path, dll_path)
    OLLAMA_URL = ollama_url
    OLLAMA_MODEL = ollama_model
    app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Flask Urdu chatbot over SQLite+vec0 retrieval + Ollama.")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--dll", default=DEFAULT_DLL)
    ap.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    ap.add_argument("--ollama-model", default=DEFAULT_OLLAMA_MODEL, help="Your local Ollama model tag (e.g., gemma2:2b, llama3.1, etc.)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    boot(args.model, args.db, args.dll, args.ollama_url, args.ollama_model, args.host, args.port, args.debug)
