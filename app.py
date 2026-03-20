import streamlit as st
import google.generativeai as genai

# Configuration de la page
st.set_page_config(page_title="IA Financial Analyst", page_icon="📈")

# --- Gestion de la Clé API ---
# On cherche d'abord dans les secrets Streamlit, sinon on demande à l'utilisateur
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Clé API Gemini non détectée. Entrez-la ici :", type="password")

if api_key:
    genai.configure(api_key=api_key)

# --- Interface Principale ---
st.title("🚀 Analyse Financière par Gemini")
st.info("Entrez un ticker boursier pour obtenir une analyse fondamentale générée par l'IA.")

ticker = st.text_input("Symbole de l'action (ex: AAPL, TSLA, MSFT) :", "").upper()

if st.button("Lancer l'Analyse"):
    if not api_key:
        st.error("Veuillez configurer votre clé API Gemini.")
    elif not ticker:
        st.warning("Veuillez entrer un symbole boursier.")
    else:
        with st.spinner(f"Analyse de {ticker} en cours..."):
            try:
                model = genai.GenerativeModel('gemini-1.5-flash-latest')
                
                prompt = f"""
                Analyse l'action {ticker} en tant qu'expert financier. 
                Structure ta réponse ainsi :
                - Présentation rapide.
                - Analyse du business model et avantages concurrentiels.
                - Risques potentiels.
                - Sentiment général du marché actuel.
                Réponds en français avec un ton professionnel.
                """
                
                response = model.generate_content(prompt)
                
                st.subheader(f"Rapport d'analyse : {ticker}")
                st.markdown("---")  # Correction ici : les guillemets ont été ajoutés
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"Erreur lors de la génération : {e}")

st.markdown("---")
st.caption("Données fournies par Google Gemini. Pas un conseil en investissement.")
