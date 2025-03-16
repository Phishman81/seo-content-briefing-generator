import streamlit as st
import openai
import pandas as pd
import requests
from bs4 import BeautifulSoup
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
openai.api_key = st.secrets["OPENAI_API_KEY"]


#################################
# 1️⃣ Eingabeoptionen
#################################

url_input = st.text_input("Website-URL (optional):", "")
text_input = st.text_area("Oder füge deinen Artikeltext hier ein (optional):", height=200)
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
# 2️⃣ Content & SEO-Analyse
##################################

def extract_text_from_url(url):
    """
    Extrahiert den Haupttext einer Webseite mit BeautifulSoup.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Versuche den Hauptinhalt aus <article>, <p>, oder einer anderen relevanten Struktur zu extrahieren
        main_content = soup.find('article')
        if main_content:
            return main_content.get_text(separator=' ')

        paragraphs = soup.find_all('p')
        if paragraphs:
            return " ".join([p.get_text() for p in paragraphs])

        return soup.get_text(separator=' ')

    except requests.exceptions.RequestException as e:
        return f"Fehler beim Abrufen der URL: {e}"

def analyze_content_with_openai(content, meta_info=None):
    """
    Erste Analyse des Artikels/Texts mit GPT.
    """
    system_msg = "Du bist ein SEO-Experte und hilfst mir, Text auf Optimierungspotenzial zu analysieren."
    user_msg = f"Hier ist ein Artikeltext:\n\n{content}\n\n"
    if meta_info:
        user_msg += f"\nZusätzliche Infos: {meta_info}\n"

    user_msg += "\nBitte fasse Stärken/Schwächen zusammen und identifiziere SEO-Optimierungspotenziale."

    response = openai.ChatCompletion.create(
        model="gpt-4",
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
# 3️⃣ Web-Recherche & Benchmarking
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

##################################
# 4️⃣ Erstellung des Texter-Briefings
##################################

def generate_seo_briefing(own_content, initial_analysis, benchmark_analysis, keywords_df, meta_info=None):
    """
    Generiert ein zusammenhängendes SEO-Briefing.
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
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
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
            benchmark_info = ""
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
        briefing_bytes = final_briefing.encode('utf-8')
        st.download_button(
            label="Briefing als TXT herunterladen",
            data=briefing_bytes,
            file_name="SEO-Briefing.txt",
            mime="text/plain"
        )
