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

SERPAPI_KEY = "833c2605f2e281d47aec475bec3ad361c317c722bf2104726a0ef6881dc2642c"
GOOGLE_API_KEY = "AIzaSyDbjJJZnl2kcZhWvz7V-80bQhgEodm6GZU"
SEOBILITY_API_KEY = "f1325c894b5664268ab10e9a185c28f8e6d63145"

# API-Limit pro Tag
API_LIMIT = 100  # Passe dies nach deinem Tarif an!

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
    api_url = f"https://api.seobility.net/seo_check?apikey={SEOBILITY_API_KEY}&url={url}"
    try:
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            if not data or "score" not in data or "quickfacts" not in data or "loadtime" not in data.get("quickfacts", {}):
                st.warning(f"Seobility: Keine verwertbaren Daten für {url}. Prüfe ob die Domain/URL geeignet ist.")
                return None, True  # True, damit ein Scan gezählt wird
            return data, True
        else:
            st.warning(f"Seobility API Fehler ({url}): Status {response.status_code}")
            return None, False
    except Exception as e:
        st.warning(f"Seobility API Fehler ({url}): {e}")
        return None, False

def extract_seo_data(seo_json):
    if seo_json is None:
        return {
            "SEO-Score": "-",
            "Ladezeit": "-"
        }
    return {
        "SEO-Score": seo_json.get("score", "-"),
        "Ladezeit": seo_json.get("quickfacts", {}).get("loadtime", "-")
    }

def get_pagespeed_score(url):
    headers = {"Content-Type": "application/json"}
    try:
        api_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&strategy=mobile&key={GOOGLE_API_KEY}"
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            score = data['lighthouseResult']['categories']['performance']['score'] * 100
            return round(score, 1)
        else:
            return "-"
    except Exception:
        return "-"

def highlight_score(val):
    try:
        val = float(val)
    except:
        return ''
    if val == "-":
        return ''
    if val <= 49:
        return 'background-color: #ff4d4d; color: white;'
    elif val <= 69:
        return 'background-color: #ffa64d; color: black;'
    elif val <= 89:
        return 'background-color: #ffff66; color: black;'
    else:
        return 'background-color: #66ff66; color: black;'

def analyze_domains(results, progress_bar):
    all_results = []

    def analyze_url(args):
        url, position = args
        # Seobility
        seo_json, api_used = seobility_api_check(url)
        seo_data = extract_seo_data(seo_json)
        # Google PageSpeed
        pagespeed_score = get_pagespeed_score(url)
        return {
            "Domain": url,
            "SEO-Score": seo_data["SEO-Score"],
            "Ladezeit (s)": seo_data["Ladezeit"],
            "PageSpeed Score": pagespeed_score,
            "api_used": api_used
        }

    total = len(results)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        batch = list(executor.map(analyze_url, results))
        for idx, res in enumerate(batch):
            progress_percent = int(((idx + 1) / total) * 100)
            progress_bar.progress(progress_percent, text=f"Prüfe Seiten… ({progress_percent}%)")
            all_results.append(res)
    progress_bar.empty()

    # API-Counter nachträglich aktualisieren (nur in Hauptprozess)
    api_calls_now = sum(1 for r in all_results if r.get("api_used"))
    st.session_state["api_scans_today"] += api_calls_now

    # Spalte "api_used" entfernen
    for r in all_results:
        r.pop("api_used", None)

    return all_results

# --- Ergebnisse anzeigen ---
if go:
    if not keyword:
        st.warning("Bitte gib ein Keyword ein.")
    else:
        st.session_state["checks_done"] += 1
        with st.spinner("Suche läuft..."):
            results = run_search(keyword, num_results)
            scans_left = API_LIMIT - st.session_state["api_scans_today"]
            if results:
                if len(results) > scans_left:
                    st.warning(f"Zu viele URLs für dein heutiges API-Limit ({API_LIMIT}). Bitte weniger Domains auswählen.")
                else:
                    progress_bar = st.progress(0, text="Seiten werden geprüft…")
                    all_results = analyze_domains(results, progress_bar)
                    if all_results:
                        df = pd.DataFrame(all_results)
                        styled_df = df.style.applymap(highlight_score, subset=["SEO-Score", "PageSpeed Score"])
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
