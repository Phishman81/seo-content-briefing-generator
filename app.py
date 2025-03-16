import openai
import streamlit as st

# Setzen des OpenAI API-Schlüssels aus den Streamlit-Secrets
openai.api_key = st.secrets["openai_api_key"]

st.title("SEO Content Briefing Generator")

# Funktion zur Generierung des Briefings
def generate_briefing(topic):
    prompt = f"Erstelle ein detailliertes SEO-Briefing zum Thema: {topic}"
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Du bist ein SEO-Experte."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        n=1,
        stop=None,
        temperature=0.7,
    )
    briefing = response.choices[0].message["content"].strip()
    return briefing

# Benutzeroberfläche
topic = st.text_input("Gib das Thema ein:")
if st.button("Briefing generieren"):
    if topic:
        with st.spinner('Generiere Briefing...'):
            briefing = generate_briefing(topic)
        st.subheader("Generiertes Briefing:")
        st.write(briefing)
    else:
        st.error("Bitte gib ein Thema ein.")
