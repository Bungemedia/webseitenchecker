import requests
import pandas as pd

# Schritt 1: Hier dein Keyword eintragen
keyword = "Sanitär Berlin"

# Schritt 2: Google-Suche simulieren (nur einfache Abfrage)
# Hinweis: wir holen nur die ersten paar Ergebnisse über eine einfache Google-Suche
# Ohne API dürfen wir Google nicht automatisch abfragen. Daher simulieren wir das hier:
search_results = [
    "https://www.ehrhard-hd.de/",
    "https://beispiel2.de",
    "https://beispiel3.de"
]

# Schritt 3: Für jede Seite einen Performance-Check machen
def check_pagespeed(url):
    api_key = "AIzaSyDbjJJZnl2kcZhWvz7V-80bQhgEodm6GZU"  # Hier musst du deinen eigenen Google API Key eintragen!
    api_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&strategy=mobile&key={api_key}"
    response = requests.get(api_url)
    if response.status_code == 200:
        data = response.json()
        score = data['lighthouseResult']['categories']['performance']['score'] * 100
        return score
    else:
        return None

# Ergebnisse sammeln
results = []

for url in search_results:
    score = check_pagespeed(url)
    if score is not None and score < 90:
        message = f"Mobile Pagespeed Score: {score}. Webseite sollte dringend optimiert werden."
        results.append({
            "Vorname": "",
            "Nachname": "",
            "Anrede": "",
            "E-Mail-Adresse": "",
            "Telefonnummer": "",
            "Mobilnummer": "",
            "Domain": url,
            "Land/Region": "Deutschland",
            "Branche": "Sanitär",
            "Nachricht": message
        })

# Ergebnisse in Excel speichern
df = pd.DataFrame(results)
df.to_excel("Ergebnisse.xlsx", index=False)
print("Die Excel-Datei 'Ergebnisse.xlsx' wurde erfolgreich erstellt!")
