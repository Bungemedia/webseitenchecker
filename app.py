import streamlit as st
import pandas as pd
import requests
import base64
import concurrent.futures
import time

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

# API-Keys
SERPAPI_KEY = "833c2605f2e281d47aec475bec3ad361c317c722bf2104726a0ef6881dc2642c"
GOOGLE_API_KEY = "AIzaSyDbjJJZnl2kcZhWvz7V-80bQhgEodm6GZU"
SEOBILITY_API_KEY = "f1325c894b5664268ab10e9a185c28f8e6d63145"

# API Limit für Seobility (z. B. 200 pro Tag im Trial oder 50k/Monat)
API_LIMIT = 100  # Setze auf deinen Wunschwert, z.B. 100 pro Tag fürs Testing

if "api_scans_today" not in st.session_state:
    st.session_state["api_scans_today"] = 0

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

def seobility_api_check(url):
    if st.session_state["api_scans_today"] >= API_LIMIT:
        st.warning("API-Limit erreicht – heute keine weiteren Scans möglich!")
        return None
    api_url = f"https://api.seobility.net/seo_check?apikey={SEOBILITY_API_KEY}&url={url}"
    try:
        response = requests.get(api_url)
        if response.status_code == 200:
            st.session_state["api_scans_today"] += 1
            time.sleep(1)  # kleine Pause zur Sicherheit
            return response.json()
        else:
            st.warning(f"Seobility API Fehler ({url}): Status {response.status_code}")
            return None
    except Exception as e:
        st.warning(f"Seobility API Fehler ({url}): {e}")
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

def categorize_score(score):
    try:
        score = float(score)
    except:
        return "-"
    if score <= 49:
        return "0-49 (schlecht)"
    elif score <= 69:
        return "50-69 (verbesserungswürdig)"
    elif score <= 89:
        return "70-89 (durchschnittlich)"
    else:
        return "90-100 (gut)"

def highlight_score(val):
    try:
        val = float(val)
    except:
        return ''
    if val <= 49:
        return 'background-color: #ff4d4d; color: white;'
    elif val <= 69:
        return 'background-color: #ffa64d; color: black;'
    elif val <= 89:
        return 'background-color: #ffff66; color: black;'
    else:
        return 'background-color: #66ff66; color: black;'

def check_pagespeed_and_seobility(results, progress_bar):
    headers = {"Content-Type": "application/json"}
    all_results = []

    def analyze_url(args):
        url, position = args
        # Google PageSpeed
        score = "-"
        category = "-"
        try:
            api_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&strategy=mobile&key={GOOGLE_API_KEY}"
            response = requests.get(api_url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                score = data['lighthouseResult']['categories']['performance']['score'] * 100
                score = round(score, 1)
                category = categorize_score(score)
        except Exception:
            pass
        # Seobility API
        seo_json = seobility_api_check(url)
        seo_data = extract_seo_data(seo_json)
        return {
            "Position": position,
            "Domain": url,
            "Score": f"{score:.1f}" if score != "-" else "-",
            "Kategorie": category,
            "SEO-Score": seo_data["SEO-Score"],
            "Ladezeit": seo_data["Ladezeit"],
            "Wörter": seo_data["Wörter"],
            "Meta-Fehler": seo_data["Meta-Fehler"],
            "Hinweise": seo_data["Hinweise"],
            "Nachricht": f"Mobile Pagespeed Score: {score:.1f}, Optimierung empfohlen!" if score != "-" else "-"
        }

    total = len(results)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        batch = list(executor.map(analyze_url, results))
        for idx, res in enumerate(batch):
            progress_percent = int(((idx + 1) / total) * 100)
            progress_bar.progress(progress_percent, text=f"Prüfe Seiten… ({progress_percent}%)")
            all_results.append(res)
    progress_bar.empty()
    return all_results

# --- Ergebnisse anzeigen ---
if go:
    if not keyword:
        st.warning("Bitte gib ein Keyword ein.")
    else:
        st.session_state["checks_done"] += 1
        with st.spinner("Suche läuft..."):
            results = run_search(keyword, num_results)
            if results:
                if len(results) > (API_LIMIT - st.session_state["api_scans_today"]):
                    st.warning(f"Zu viele URLs für dein heutiges API-Limit ({API_LIMIT}). Bitte weniger Domains auswählen.")
                else:
                    progress_bar = st.progress(0, text="Seiten werden geprüft…")
                    all_results = check_pagespeed_and_seobility(results, progress_bar)
                    if all_results:
                        df = pd.DataFrame(all_results).sort_values(by="Position")
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
        st.info(f"Heute bereits genutzte API-Scans: {st.session_state['api_scans_today']} / {API_LIMIT}")

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
