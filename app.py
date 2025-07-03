import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import base64
import json
import os

st.set_page_config(page_title="Webseiten-Checker", page_icon="logo.png", layout="centered")

# --- LOGO einlesen ---
def get_base64_logo(file_path):
    with open(file_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()
    return encoded

logo_base64 = get_base64_logo("logo.png")

# --- Dark Theme & zentrierte Headline ---
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] {
        background: #181a1e !important;
        color: #fff !important;
    }
    .stTextInput>div>div>input {
        background: #222 !important;
        color: #fff !important;
        border-radius: 12px !important;
        padding: 0.6em 1em !important;
        border: 1px solid #2b2e32 !important;
    }
    .stButton > button {
        background: linear-gradient(90deg, #132c57 0%, #223a5e 100%) !important;
        color: white !important;
        font-weight: bold;
        border-radius: 14px;
        border: none;
        padding: 0.7em 2em;
        margin-bottom: 1em;
        box-shadow: 0 2px 12px #132c5730;
        transition: background 0.3s;
    }
    .stButton > button:hover {
        background: linear-gradient(90deg, #223a5e 0%, #132c57 100%) !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown(
    f"""
    <div style='text-align:center; margin-bottom:0.7em;'>
        <a href="https://bungemedia.de/" target="_blank">
            <img src="data:image/png;base64,{logo_base64}" width="72" style="margin-bottom: -7px; border-radius: 10px; box-shadow:0 2px 8px #0004;">
        </a>
        <h1 style='color:#fff; font-weight:800; margin-top:0.7em; margin-bottom:0;'>Webseiten-Checker</h1>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Eingabefelder ---
col1, col2 = st.columns([2, 1])
with col1:
    keyword = st.text_input("Keyword eingeben", "")
with col2:
    num_results = st.selectbox("Anzahl Ergebnisse", [1, 5, 10, 20, 30], index=1)

go = st.button("Scan starten")

if "checks_done" not in st.session_state:
    st.session_state["checks_done"] = 0

SERPAPI_KEY = "833c2605f2e281d47aec475bec3ad361c317c722bf2104726a0ef6881dc2642c"
GOOGLE_API_KEY = "AIzaSyDbjJJZnl2kcZhWvz7V-80bQhgEodm6GZU"

def run_search(keyword, num_results):
    params = {
        "engine": "google",
        "q": keyword,
        "location": "Germany",
        "num": num_results,
        "api_key": SERPAPI_KEY
    }
    try:
        response = requests.get("https://serpapi.com/search", params=params)
        if response.status_code == 200:
            results = response.json()
            organic_results = results.get("organic_results", [])
            return [(res["link"], idx + 1) for idx, res in enumerate(organic_results) if "link" in res]
        else:
            st.error(f"Fehler bei der Google-Suche: Statuscode {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Fehler bei der Google-Suche: {e}")
        return []

def seo_scrape(url):
    try:
        r = requests.get(url, timeout=4)
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else "-"
        meta = soup.find("meta", attrs={"name": "description"})
        meta_desc = meta["content"].strip() if meta and "content" in meta.attrs else "-"
        return title, meta_desc
    except Exception:
        return "-", "-"

def check_legal(url):
    url = url.rstrip("/")
    impressum = False
    datenschutz = False
    try:
        r = requests.get(url + "/impressum", timeout=3)
        impressum = r.status_code == 200
    except Exception:
        pass
    try:
        r = requests.get(url + "/datenschutz", timeout=3)
        datenschutz = r.status_code == 200
    except Exception:
        pass
    return ("Ja" if impressum else "Nein"), ("Ja" if datenschutz else "Nein")

def categorize_score(score):
    score = float(score)
    if score <= 49:
        return "0-49 (schlecht)"
    elif score <= 69:
        return "50-69 (verbesserungswürdig)"
    elif score <= 89:
        return "70-89 (durchschnittlich)"
    else:
        return "90-100 (gut)"

def highlight_score(val):
    val = float(val)
    if val <= 49:
        return 'background-color: #ff4d4d; color: white;'
    elif val <= 69:
        return 'background-color: #ffa64d; color: black;'
    elif val <= 89:
        return 'background-color: #ffff66; color: black;'
    else:
        return 'background-color: #66ff66; color: black;'

# --- NEU: JSON-SEO-Report einlesen und Felder extrahieren ---
def load_seo_json(url):
    # Aus URL den Dateinamen machen, z.B. example.com => report_example.com.json
    domain = url.replace("https://", "").replace("http://", "").split("/")[0]
    filename = f"report_{domain}.json"
    if os.path.isfile(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    else:
        return None

def extract_seo_data(seo_json):
    if seo_json is None:
        return {
            "SEO-Score": "-",
            "Ladezeit": "-",
            "Wörter": "-",
            "Meta-Fehler": "-",
            "Hinweise": "-"
        }
    return {
        "SEO-Score": seo_json.get("score", "-"),
        "Ladezeit": seo_json.get("quickfacts", {}).get("loadtime", "-"),
        "Wörter": seo_json.get("quickfacts", {}).get("words", "-"),
        "Meta-Fehler": "Ja" if any("meta description" in h["text"].lower() for h in seo_json.get("hints", [])) else "Nein",
        "Hinweise": ", ".join([h["text"] for h in seo_json.get("hints", [])][:3])
    }

def check_pagespeed(results, progress_bar):
    headers = {"Content-Type": "application/json"}
    pagespeed_results = []
    total = len(results)
    for idx, (url, position) in enumerate(results):
        api_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&strategy=mobile&key={GOOGLE_API_KEY}"
        try:
            response = requests.get(api_url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                score = data['lighthouseResult']['categories']['performance']['score'] * 100
                score = round(score, 1)
                # SEO-Infos aus JSON einlesen
                seo_json = load_seo_json(url)
                seo_data = extract_seo_data(seo_json)
                title, meta_desc = seo_scrape(url)
                impressum, datenschutz = check_legal(url)
                category = categorize_score(score)
                pagespeed_results.append({
                    "Position": position,
                    "Domain": url,
                    "Score": f"{score:.1f}",
                    "Kategorie": category,
                    "Title": title,
                    "Meta Description": meta_desc,
                    "Impressum": impressum,
                    "Datenschutz": datenschutz,
                    # Die neuen Felder:
                    "SEO-Score": seo_data["SEO-Score"],
                    "Ladezeit": seo_data["Ladezeit"],
                    "Wörter": seo_data["Wörter"],
                    "Meta-Fehler": seo_data["Meta-Fehler"],
                    "Hinweise": seo_data["Hinweise"],
                    "Nachricht": f"Mobile Pagespeed Score: {score:.1f}, Optimierung empfohlen!"
                })
            else:
                st.warning(f"Fehler bei {url}: Statuscode {response.status_code}")
        except Exception as e:
            st.warning(f"Fehler bei {url}: {e}")
        progress_percent = int(((idx + 1) / total) * 100)
        progress_bar.progress(progress_percent, text=f"Prüfe Seiten… ({progress_percent}%)")
    progress_bar.empty()
    return pagespeed_results

# --- Ergebnisse anzeigen ---
if go:
    if not keyword:
        st.warning("Bitte gib ein Keyword ein.")
    else:
        st.session_state["checks_done"] += 1
        with st.spinner("Suche läuft..."):
            results = run_search(keyword, num_results)
            if results:
                progress_bar = st.progress(0, text="Seiten werden geprüft…")
                pagespeed_results = check_pagespeed(results, progress_bar)
                if pagespeed_results:
                    df = pd.DataFrame(pagespeed_results).sort_values(by="Position")
                    df = df.reset_index(drop=True)
                    styled_df = df.style.applymap(highlight_score, subset=["Score"])
                    st.subheader("🔎 Detaillierte Ergebnisse")
                    st.dataframe(styled_df, hide_index=True)
                    st.success("Analyse abgeschlossen!")
                else:
                    st.info("Keine Webseiten mit ausreichender Bewertung gefunden.")
            else:
                st.info("Keine Ergebnisse für das Keyword gefunden.")
        st.info(f"Checks in dieser Session: {st.session_state['checks_done']}")

# --- INFO-Text, Footer, Kontaktbereich ---
st.markdown("---")
st.markdown("""
<div style='text-align:center; color: #bbb; font-size: 0.95em;'>
    <b>Webseiten-Checker</b> | Ein Projekt von BungeMedia<br>
    Kontakt: <a href="mailto:info@bungemedia.de" style="color:#6af">info@bungemedia.de</a> <br>
    <a href="https://bungemedia.de/impressum/" style="color:#6af">Impressum</a> | 
    <a href="https://bungemedia.de/datenschutzerklaerung/" style="color:#6af">Datenschutz</a>
</div>
""", unsafe_allow_html=True)
