import streamlit as st
import google.generativeai as genai
import yfinance as yf

# Configuration
st.set_page_config(page_title="IA Stock Analyst 2026", page_icon="💰")

# --- Gestion de la Clé API ---
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Clé API Gemini :", type="password")

if api_key:
    genai.configure(api_key=api_key)

# --- Fonctions de Données (avec Cache) ---
@st.cache_data(ttl=3600)  # Garde en mémoire pendant 1h pour éviter de surcharger YF
def get_stock_data(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)
    info = stock.info
    # Extraction de quelques metrics clés
    data_summary = {
        "Nom": info.get("longName"),
        "Prix Actuel": info.get("currentPrice"),
        "PER": info.get("trailingPE"),
        "Dividende": info.get("dividendYield"),
        "Secteur": info.get("sector"),
        "Résumé": info.get("longBusinessSummary")[:500] # Limité pour le prompt
    }
    return data_summary

# --- Interface ---
st.title("📈 Analyse Financière Hybride")
st.write("Données réelles (Yahoo Finance) + Intelligence Artificielle (Gemini 2.5 Flash)")

ticker = st.text_input("Entrez le ticker (ex: NVDA, MC.PA, TSLA) :", "").upper()

if st.button("Analyser l'action"):
    if not api_key:
        st.error("Configurez votre clé API.")
    elif not ticker:
        st.warning("Entrez un ticker.")
    else:
        try:
            with st.spinner("Récupération des données boursières..."):
                data = get_stock_data(ticker)
            
            # Affichage des données brutes
            col1, col2, col3 = st.columns(3)
            col1.metric("Prix", f"{data['Prix Actuel']} $")
            col2.metric("PER", f"{data['PER']:.2f}" if data['PER'] else "N/A")
            col3.metric("Rendement", f"{data['Dividende']*100:.2f} %" if data['Dividende'] else "0 %")

            with st.spinner("Gemini analyse les chiffres..."):
                # Utilisation du modèle validé par ton diagnostic
                model = genai.GenerativeModel('models/gemini-2.5-flash')
                
                prompt = f"""
                Analyse l'action {data['Nom']} ({ticker}) basée sur ces données réelles :
                - Secteur : {data['Secteur']}
                - Prix : {data['Prix Actuel']}
                - PER : {data['PER']}
                - Business : {data['Résumé']}
                
                En tant qu'analyste, donne ton avis sur la valorisation actuelle et les perspectives. 
                Sois concis et structure avec des émojis. Réponds en français.
                """
                
                response = model.generate_content(prompt)
                
                st.subheader("💡 Analyse de l'IA")
                st.markdown("---")
                st.markdown(response.text)

        except Exception as e:
            st.error(f"Erreur : Vérifiez que le ticker est valide. Détails : {e}")

st.markdown("---")
st.caption("Données Yahoo Finance mises en cache. Analyse par Gemini 2.5 Flash.")
