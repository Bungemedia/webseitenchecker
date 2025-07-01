import streamlit as st
import pandas as pd
import requests

# --- ZENTRIERUNG, STYLE, DARK THEME ---
st.set_page_config(page_title="Webseiten-Checker", page_icon="logo.png", layout="centered")

st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] {
        background: #181a1e !important;
        color: #fff !important;
        height: 100%;
        min-height: 100vh;
    }
    .main-center {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        min-height: 92vh;
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
    label[for^="text_input"] {
        color: #fff !important;
        font-weight: 500;
        font-size: 1.05em;
        letter-spacing: 0.5px;
    }
    .center-headline {
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    </style>
""", unsafe_allow_html=True)

# --- ALLES IN ZENTRIERTEM DIV ---
st.markdown('<div class="main-center">', unsafe_allow_html=True)

# --- HEADER: Logo & Headline ---
st.markdown('<div class="center-headline">', unsafe_allow_html=True)
st.image("logo.png", width=80)
st.markdown("<h1 style='margin-bottom:0.4em; color:#fff;'>Webseiten-Checker</h1>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- SUBTITLE ---
st.markdown("<div style='text-align:center; margin-bottom:1.5em; color:#fff;'>Finde Webseiten, die Optimierung brauchen!</div>", unsafe_allow_html=True)

# --- EINGABE ---
keyword = st.text_input("Keyword eingeben", "")
go = st.button("Scan starten")

st.markdown('</div>', unsafe_allow_html=True)  # Zentrier-Container schließen

# --- FUNKTIONEN ---
SERPAPI_KEY = "833c2605f2e281d47aec475bec3ad361c317c722bf2104726a0ef6881dc2642c"
GOOGLE_API_KEY = "AIzaSyDbjJJZnl2kcZhWvz7V-80bQhgEodm6GZU"

def run_search(keyword):
    params = {
        "engine": "google",
        "q": keyword,
        "location": "Germany",
        "num": 10,
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
                category = categorize_score(score)
                pagespeed_results.append({
                    "Position": position,
                    "Domain": url,
                    "Score": score,
                    "Kategorie": category,
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

def categorize_score(score):
    if score <= 49:
        return "0-49 (schlecht)"
    elif score <= 69:
        return "50-69 (verbesserungswürdig)"
    elif score <= 89:
        return "70-89 (durchschnittlich)"
    else:
        return "90-100 (gut)"

def highlight_score(val):
    if val <= 49:
        return 'background-color: #ff4d4d; color: white;'
    elif val <= 69:
        return 'background-color: #ffa64d; color: black;'
    elif val <= 89:
        return 'background-color: #ffff66; color: black;'
    else:
        return 'background-color: #66ff66; color: black;'

# --- ERGEBNISSE (NACH BUTTON CLICK) ---
if go:
    if not keyword:
        st.warning("Bitte gib ein Keyword ein.")
    else:
        with st.spinner("Suche läuft..."):
            results = run_search(keyword)
            if results:
                progress_bar = st.progress(0, text="Seiten werden geprüft…")
                pagespeed_results = check_pagespeed(results, progress_bar)
                if pagespeed_results:
                    df = pd.DataFrame(pagespeed_results).sort_values(by="Position")
                    styled_df = df.style.applymap(highlight_score, subset=["Score"])
                    st.subheader("🔎 Detaillierte Ergebnisse")
                    st.dataframe(styled_df)
                    st.success("Analyse abgeschlossen!")
                else:
                    st.info("Keine Webseiten mit ausreichender Bewertung gefunden.")
            else:
                st.info("Keine Ergebnisse für das Keyword gefunden.")
