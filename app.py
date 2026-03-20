import streamlit as st
import google.generativeai as genai
import yfinance as yf
import pandas as pd

# 1. Configuration de la page
st.set_page_config(page_title="IA Financial Analyst Pro", page_icon="⚖️", layout="wide")

# 2. Gestion de la Clé API (Secrets ou Sidebar)
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Clé API Gemini :", type="password")

if api_key:
    genai.configure(api_key=api_key)

# 3. Récupération des données (Optimisée avec Cache)
@st.cache_data(ttl=3600)
def get_full_analysis_data(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)
    info = stock.info
    
    # Ratios et Valeurs Clés
    data = {
        "name": info.get("longName", "N/A"),
        "price": info.get("currentPrice"),
        "market_cap": info.get("marketCap"),
        "per_actual": info.get("trailingPE"),
        "per_forward": info.get("forwardPE"),
        "yield_actual": (info.get("dividendYield", 0) or 0) * 100,
        "yield_5y_avg": info.get("fiveYearAvgDividendYield", "N/A"),
        "roe": (info.get("returnOnEquity", 0) or 0) * 100,
        "debt_equity": info.get("debtToEquity"),
        "marge_ope": (info.get("operatingMargins", 0) or 0) * 100,
        "summary": info.get("longBusinessSummary", "")[:800]
    }
    return data

def format_bn(num):
    if not num: return "N/A"
    return f"{num/1e9:.2f} Md $" if num > 1e9 else f"{num/1e6:.2f} M $"

# --- INTERFACE PRINCIPALE ---
st.title("⚖️ Analyseur de Valeur Fondamentale")
ticker = st.text_input("Symbole Boursier", "AAPL").upper()

if st.button("Lancer l'Analyse Complète"):
    if not api_key:
        st.error("Clé API manquante.")
    else:
        try:
            # --- PHASE 1 : DONNÉES ---
            with st.spinner("Extraction des données Yahoo Finance..."):
                d = get_full_analysis_data(ticker)
            
            st.header(f"Rapport : {d['name']} ({ticker})")
            
            # Affichage rapide en colonnes
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Prix", f"{d['price']} $")
            c2.metric("Market Cap", format_bn(d['market_cap']))
            c3.metric("PER Actuel", f"{d['per_actual']:.2f}" if d['per_actual'] else "N/A")
            c4.metric("Rendement", f"{d['yield_actual']:.2f} %")

            # --- PHASE 2 : ANALYSE IA ---
            with st.spinner("Analyse stratégique par Gemini 2.5 Flash..."):
                model = genai.GenerativeModel('models/gemini-2.5-flash')
                
                # Le prompt contient maintenant toutes les variables extraites
                prompt = f"""
                Agis en tant qu'analyste financier expert en "Value Investing".
                Analyse l'action {d['name']} ({ticker}) avec les données suivantes :
                - Valorisation : PER Actuel {d['per_actual']}, PER Futur {d['per_forward']}.
                - Rendement : {d['yield_actual']}% (Moyenne 5 ans : {d['yield_5y_avg']}%).
                - Rentabilité : ROE {d['roe']:.2f}%, Marge Opérationnelle {d['marge_ope']:.2f}%.
                - Santé : Dette/Equity {d['debt_equity']}.
                - Business : {d['summary']}

                Instructions :
                1. Compare le PER actuel au PER futur pour juger la croissance attendue.
                2. Analyse si le rendement dividende actuel est une opportunité par rapport à l'historique (5y avg).
                3. Évalue la solidité du bilan (Dette/Equity).
                4. Donne un verdict final (Surévalué, Sous-évalué ou Juste Prix) et les points de vigilance.
                Réponds en français de manière structurée.
                """
                
                response = model.generate_content(prompt)
                
                st.subheader("🤖 Analyse Stratégique de l'IA")
                st.markdown("---")
                st.markdown(response.text)

        except Exception as e:
            st.error(f"Une erreur est survenue : {e}")

st.divider()
st.caption("Sources : Yahoo Finance API & Google Gemini 2.5 Flash.")
