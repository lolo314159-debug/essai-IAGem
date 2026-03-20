import streamlit as st
import google.generativeai as genai

# Configuration de la page
st.set_page_config(page_title="IA Financial Analyst", page_icon="📈")

# --- Interface Latérale (Configuration) ---
with st.sidebar:
    st.title("Settings")
    api_key = st.text_input("Entrez votre clé API Gemini :", type="password")
    if api_key:
        genai.configure(api_key=api_key)
    
    st.info("Cette application utilise l'IA pour analyser le sentiment de marché et les perspectives d'une action.")

# --- Interface Principale ---
st.title("🚀 Analyse Financière par Gemini")

ticker = st.text_input("Entrez le symbole de l'action (ex: AAPL, TSLA, MSFT) :", "").upper()

if st.button("Lancer l'Analyse"):
    if not api_key:
        st.error("Veuillez configurer votre clé API dans la barre latérale.")
    elif not ticker:
        st.warning("Veuillez entrer un symbole boursier.")
    else:
        with st.spinner(f"Analyse de {ticker} en cours par Gemini..."):
            try:
                # Initialisation du modèle
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Prompt structuré pour l'analyse
                prompt = f"""
                En tant qu'analyste financier expert, fournis une analyse concise pour l'action {ticker}.
                L'analyse doit inclure :
                1. Une brève présentation de l'entreprise.
                2. Les points forts (Moats) et les risques actuels.
                3. Une analyse du sentiment de marché récent.
                4. Une conclusion sur la perspective à long terme.
                Réponds en français et utilise des émojis pour la lisibilité.
                """
                
                response = model.generate_content(prompt)
                
                # Affichage des résultats
                st.subheader(f"Rapport d'analyse : {ticker}")
                st.markdown(---)
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"Une erreur est survenue : {e}")

# Footer
st.markdown("---")
st.caption("Note : Les analyses générées par IA ne constituent pas des conseils financiers professionnels.")
