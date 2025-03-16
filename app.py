# Filename: app.py

import streamlit as st
import openai
import pandas as pd

import requests
from bs4 import BeautifulSoup
from newspaper import Article
from googlesearch import search

import io

############################
# Streamlit App Hauptstruktur
############################

st.set_page_config(page_title="SEO-Briefing Generator", layout="wide")

st.title("SEO Content Briefing Generator")
st.write("""
Erstelle automatisiert ein detailliertes Briefing für Content-Optimierungen.
Gib eine URL oder einen Text ein, lade optional Keyword-Daten hoch und 
erhalte auf Basis der KI-Analyse (und Benchmarking) ein fertiges Texter-Briefing.
""")

# Setup OpenAI API-Key aus Streamlit Secrets
#   -> Füge deinen Key in den Streamlit Cloud Secrets ein (Settings -> Secrets)
openai.api_key = st.secrets["OPENAI_API_KEY"]


#################################
# 1️⃣ Eingabeoptionen
#################################

# Eingabefelder für URL und/oder Text
url_input = st.text_input("Website-URL (optional):", "")
text_input = st.text_area("Oder füge deinen Artikeltext hier ein (optional):", height=200)

# Zusätzliche optionale Felder
zielgruppe = st.text_input("Zielgruppe (optional):", "")
ziel_des_artikels = st.text_input("Ziel des Artikels (optional):", "")
fokus_keyword = st.text_input("Fokus-Keyword (optional):", "")

st.write("**Optional: Lade eine CSV-Datei mit Keyword-Daten hoch (Spalten: 'Keyword', 'Search Volume')**")
uploaded_file = st.file_uploader("CSV-Datei hochladen", type=["csv"])
keywords_df = None
if uploaded_file is not None:
    try:
        keywords_df = pd.read_csv(uploaded_file)
        st.write("**Vorschau auf Keyword-Daten:**")
        st.dataframe(keywords_df.head())
    except Exception as e:
        st.error(f"Fehler beim Lesen der Datei: {e}")


##################################
# 2️⃣ Analyse-Phase 1: Content & SEO-Analyse
##################################

def extract_text_from_url(url):
    """
    Extrahiert Artikeltext aus einer URL mit Newspaper3k.
    Fallback mit BeautifulSoup, falls Newspaper fehlschlägt.
    """
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        # Backup-Methode: requests + BeautifulSoup
        try:
            resp = requests.get(url)
            soup = BeautifulSoup(resp.text, 'html.parser')
            return soup.get_text(separator=' ')
        except:
            return ""

def analyze_content_with_openai(content, meta_info=None):
    """
    Erste Analyse des Artikels/Texts mit GPT.
    meta_info kann Infos wie Zielgruppe, Fokus-Keyword etc. enthalten.
    """
    system_msg = "Du bist ein SEO-Experte und hilfst mir, Text auf Optimierungspotenzial zu analysieren."
    user_msg = f"Hier ist ein Artikeltext:\n\n{content}\n\n"
    if meta_info:
        user_msg += f"\nZusätzliche Infos: {meta_info}\n"

    user_msg += "\nBitte fasse Stärken/Schwächen zusammen und identifiziere SEO-Optimierungspotenziale."

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ],
        temperature=0.7,
        max_tokens=800
    )
    return response.choices[0].message["content"]


content_to_analyze = ""
if url_input and text_input:
    st.warning("Es wurde sowohl eine URL als auch ein Text eingegeben. Bevorzugt wird der direkt eingegebene Text.")
    content_to_analyze = text_input.strip()
elif url_input and not text_input:
    content_to_analyze = extract_text_from_url(url_input).strip()
elif text_input and not url_input:
    content_to_analyze = text_input.strip()

analysis_result = None
if st.button("Jetzt analysieren"):
    if not content_to_analyze:
        st.error("Bitte gib mindestens eine URL oder einen direkten Text ein.")
    else:
        meta_info = f"Zielgruppe: {zielgruppe}, Ziel: {ziel_des_artikels}, Fokus-Keyword: {fokus_keyword}"
        analysis_result = analyze_content_with_openai(content_to_analyze, meta_info)
        st.subheader("Erste Analyse deines Textes")
        st.write(analysis_result)


##################################
# 3️⃣ Analyse-Phase 2: Web-Recherche & Benchmarking
##################################

def perform_google_search(query, num_results=5):
    """
    Führt eine Google-Suche aus und gibt die Top-URLs zurück.
    """
    results = []
    try:
        for url in search(query, num_results=num_results):
            results.append(url)
    except Exception as e:
        st.warning(f"Fehler bei Google-Suche: {e}")
    return results

def extract_competitor_data(urls):
    """
    Extrahiert Texte aus den Top-URLs und gibt eine Liste von Strings zurück (pro URL ein Artikel).
    """
    texts = []
    for u in urls:
        txt = extract_text_from_url(u).strip()
        texts.append({"url": u, "text": txt, "word_count": len(txt.split())})
    return texts

def benchmark_analysis_with_openai(own_content, competitors_info, meta_info=None):
    """
    Erzeugt eine Benchmark-Analyse mit GPT. Schickt KI: eigenen Content + Infos zu den Konkurrenztexten.
    """
    system_msg = "Du bist ein erfahrener SEO und Content-Analyst. Du vergleichst mehrere Texte zu demselben Thema."
    
    competitor_summaries = ""
    for c in competitors_info:
        competitor_summaries += f"URL: {c['url']}\nWortanzahl: {c['word_count']}\nTextauszug:\n{c['text'][:1000]}\n\n"
    
    user_msg = f"""Mein eigener Artikeltext:
    {own_content[:1500]}

    Hier sind Auszüge aus Artikeln, die in Google top ranken:
    {competitor_summaries}

    Bitte vergleiche meinen Artikel mit diesen Top-Artikeln:
    - Welche inhaltlichen Themen decken die Wettbewerber ab, die mir fehlen?
    - Welche Textlänge, Keyword-Fokus, Struktur sind bei den Top-Artikeln üblich?
    - Wo siehst du Content-Gaps?
    """
    if meta_info:
        user_msg += f"\nZusätzliche Meta-Infos: {meta_info}\n"

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ],
        temperature=0.7,
        max_tokens=1000
    )
    return response.choices[0].message["content"]

benchmark_result = None
if analysis_result:  # Nur ausführen, wenn schon eine Analyse da ist
    with st.expander("Optional: Benchmark-Analyse starten"):
        st.write("Basierend auf deinem Fokus-Keyword wird nach Konkurrenz-Artikeln gesucht.")
        st.write("Achtung: Google-Scraping kann fehleranfällig sein. Nutze es verantwortungsvoll.")
        benchmark_trigger = st.button("Benchmark durchführen")
        if benchmark_trigger:
            if not fokus_keyword:
                st.warning("Bitte gib ein Fokus-Keyword an, damit die Benchmark-Suche durchgeführt werden kann.")
            else:
                with st.spinner("Suche nach Top-Artikeln..."):
                    competitor_urls = perform_google_search(fokus_keyword, num_results=3)
                    st.write("Gefundene Top-URLs:", competitor_urls)
                    competitor_texts = extract_competitor_data(competitor_urls)
                with st.spinner("Vergleiche Inhalte mit OpenAI..."):
                    meta_info_2 = f"Fokus-Keyword: {fokus_keyword}"
                    benchmark_result = benchmark_analysis_with_openai(content_to_analyze, competitor_texts, meta_info_2)
                    st.subheader("Ergebnisse der Benchmark-Analyse")
                    st.write(benchmark_result)


##################################
# 4️⃣ Erstellung des Texter-Briefings
##################################

def generate_seo_briefing(own_content, initial_analysis, benchmark_analysis, keywords_df, meta_info=None):
    """
    Generiert ein zusammenhängendes SEO-Briefing, das alle Infos (eigener Artikel, 
    Benchmark, Keyword-Daten) einbezieht.
    """
    system_msg = "Du bist ein professioneller SEO-Briefing-Assistent."
    user_msg = f"""
    Mein eigener Artikel (Kurzfassung, max. 1000 Zeichen):
    {own_content[:1000]}
    
    Erste Analyse (Stärken/Schwächen):
    {initial_analysis}

    Benchmark-Analyse:
    {benchmark_analysis}

    """
    if keywords_df is not None:
        # Füge eine kompakte Darstellung der Keyword-Daten in den Prompt ein
        # Nur Top 10 Zeilen, um den Prompt nicht zu sprengen
        df_head = keywords_df.head(10)
        kw_string = df_head.to_csv(index=False)
        user_msg += f"\nHier sind einige relevante Keywords mit Suchvolumen:\n{kw_string}\n"
    
    if meta_info:
        user_msg += f"\nKontext: {meta_info}\n"

    user_msg += """
    Bitte erstelle nun ein strukturiertes SEO-Texter-Briefing:

    1. Kurze Zusammenfassung des bestehenden Artikels
    2. Content-Gaps und empfohlene Änderungen/Ergänzungen
    3. Vorschläge für Textstruktur und Absatzthemen
    4. Keyword-Empfehlungen (Fokus und Nebenkeywords) inkl. Platzierung
    5. Aktualisierungen auf Basis aktueller Trends/Infos
    6. Weitere SEO-Hinweise (z.B. Meta-Daten, interne Verlinkung, EEAT)

    Das Briefing soll so geschrieben sein, dass ein Texter es direkt umsetzen kann.
    """
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ],
        temperature=0.7,
        max_tokens=1500
    )
    return response.choices[0].message["content"]

final_briefing = None
if st.button("SEO-Briefing generieren"):
    if not analysis_result:
        st.error("Bitte zuerst eine Analyse durchführen.")
    else:
        with st.spinner("Generiere dein SEO-Briefing..."):
            # Optional: Benchmark-Analyse Einbindung (wenn vorhanden)
            benchmark_info = benchmark_result if benchmark_result else ""
            meta_info_3 = f"Zielgruppe: {zielgruppe}, Ziel des Artikels: {ziel_des_artikels}, Fokus-Keyword: {fokus_keyword}"
            final_briefing = generate_seo_briefing(
                content_to_analyze,
                analysis_result,
                benchmark_info,
                keywords_df,
                meta_info=meta_info_3
            )
        st.subheader("Dein SEO-Briefing")
        st.write(final_briefing)
        # Optional: Download-Button
        briefing_bytes = final_briefing.encode('utf-8')
        st.download_button(
            label="Briefing als TXT herunterladen",
            data=briefing_bytes,
            file_name="SEO-Briefing.txt",
            mime="text/plain"
        )
