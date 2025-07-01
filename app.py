import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from st_aggrid import AgGrid, GridOptionsBuilder

st.set_page_config(page_title="Webseiten-Checker", page_icon="logo.png", layout="centered")

# --- CLEAN DARK THEME & HEADLINE ZENTRIERUNG ---
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

# ---- OBEN: LOGO MIT HOMEPAGE-LINK UND HEADLINE ----
st.markdown(
    """
    <div style='text-align:center; margin-bottom:0.7em;'>
        <a href="https://bungemedia.de/" target="_blank">
            <img src="logo.png" width="72" style="margin-bottom: -7px;" />
        </a>
        <h1 style='display:inline-block; vertical-align: middle; margin-left:0.3em; color:#fff; font-weight:800;'>Webseiten-Checker</h1>
    </div>
    """,
    unsafe_allow_html=True
)
st.markdown(
    "<div style='text-align:center; margin-bottom:2.2em; color:#fff;'>Finde Webseiten, die Optimierung brauchen!</div>",
    unsafe_allow_html=True
)

# --- Weitere Eingabefelder ---
col1, col2 = st.columns([2, 1])
with col1:
    keyword = st.text_input("Keyword eingeben", "")
with col2:
    num_results = st.selectbox("Anzahl Ergebnisse", [5, 10, 20, 30], index=1)

go = st.button("Scan starten")

# --- Session-Statistik ---
if "checks_done" not in st.session_state:
    st.session_state["checks_done"] = 0

# --- API-Keys ---
SERPAPI_KEY = "833c2605f2e281d47aec475bec3ad361c317c722bf2104726a0ef6881dc2642c"
GOOGLE_API_KEY = "AIzaSyDbjJJZnl2kcZhWvz7V-80bQhgEodm6GZU"

# --- Funktionen ---
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
    """SEO-Checks: Titel und Meta-Description scrapen"""
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
    """Checkt, ob Impressum/Datenschutz vorhanden ist"""
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
                # Nur Seiten < 90% aufnehmen!
                if score >= 90:
                    continue

                # SEO-Checks
                title, meta_desc = seo_scrape(url)

                # Impressum/Datenschutz
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
    score = float(score)
    if score <= 49:
        return "0-49 (schlecht)"
    elif score <= 69:
        return "50-69 (verbesserungswürdig)"
    elif score <= 89:
        return "70-89 (durchschnittlich)"
    else:
        return "90-100 (gut)"

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
                    df = df.reset_index(drop=True)  # entfernt die zusätzliche Index-Spalte

                    # --- AgGrid-Konfiguration ---
                    gb = GridOptionsBuilder.from_dataframe(df)
                    gb.configure_pagination(enabled=True)
                    gb.configure_default_column(groupable=False, editable=False, resizable=True)
                    gb.configure_column(
                        "Score",
                        cellStyle=lambda params: {
                            'color': 'white',
                            'backgroundColor': (
                                '#ff4d4d' if float(params.value) <= 49 else
                                '#ffa64d' if float(params.value) <= 69 else
                                '#ffff66' if float(params.value) <= 89 else
                                '#66ff66'
                            )
                        }
                    )
                    gridOptions = gb.build()
                    st.subheader("🔎 Detaillierte Ergebnisse")
                    AgGrid(
                        df,
                        gridOptions=gridOptions,
                        theme="streamlit",
                        height=400,
                        fit_columns_on_grid_load=True
                    )
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

