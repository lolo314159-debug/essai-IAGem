import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats
import google.generativeai as genai

# --- Configuration de la Page ---
st.set_page_config(page_title="Terminal Quant & IA", layout="wide")

# Gestion de la Clé API
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Clé API Gemini :", type="password")

if api_key:
    genai.configure(api_key=api_key)

# --- Fonctions de Récupération & Calculs ---
@st.cache_data(ttl=3600)
def fetch_all_data(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)
    info = stock.info
    hist = stock.history(start="2000-01-01")
    
    if hist.empty:
        return None, None
    
    # Compilation exhaustive des métriques
    metrics = {
        "Nom": info.get("longName", "N/A"),
        "Secteur": info.get("sector", "N/A"),
        "Prix Actuel": info.get("currentPrice"),
        "Market Cap": info.get("marketCap"),
        "Revenue TTM": info.get("totalRevenue"),
        "Net Income TTM": info.get("netIncomeToCommon"),
        "PER Trailing": info.get("trailingPE"),
        "PER Forward": info.get("forwardPE"),
        "P/S Ratio": info.get("priceToSalesTrailing12Months"),
        "Yield (%)": (info.get("dividendYield") or 0) * 100,
        "Yield 5Y Avg": info.get("fiveYearAvgDividendYield"),
        "ROE (%)": (info.get("returnOnEquity") or 0) * 100,
        "Operating Margin (%)": (info.get("operatingMargins") or 0) * 100,
        "Debt/Equity": info.get("debtToEquity"),
        "Payout Ratio (%)": (info.get("payoutRatio") or 0) * 100,
        "52W High": info.get("fiftyTwoWeekHigh"),
        "52W Low": info.get("fiftyTwoWeekLow"),
        "Summary": info.get("longBusinessSummary", "")[:1000]
    }
    return hist, metrics

def calculate_log_regression(df):
    df = df.copy()
    df['Log_Price'] = np.log(df['Close'])
    df['Days'] = np.arange(len(df))
    
    slope, intercept, r_value, p_value, std_err = stats.linregress(df['Days'], df['Log_Price'])
    
    df['Reg_Log'] = intercept + slope * df['Days']
    residuals = df['Log_Price'] - df['Reg_Log']
    std_dev = np.std(residuals)
    
    # Calcul des courbes en échelle réelle
    df['Reg_Price'] = np.exp(df['Reg_Log'])
    df['Upper_1s'] = np.exp(df['Reg_Log'] + std_dev)
    df['Lower_1s'] = np.exp(df['Reg_Log'] - std_dev)
    df['Upper_2s'] = np.exp(df['Reg_Log'] + 2 * std_dev)
    df['Lower_2s'] = np.exp(df['Reg_Log'] - 2 * std_dev)
    
    return df, std_dev, r_value**2

def format_val(val):
    if val is None or val == "N/A": return "N/A"
    if val >= 1e12: return f"{val/1e12:.2f} T$"
    if val >= 1e9: return f"{val/1e9:.2f} Md$"
    return f"{val:,.0f}$"

# --- Interface Utilisateur ---
st.title("🚀 Terminal d'Analyse Fondamentale & Quantitative")
ticker = st.text_input("Entrez le Ticker (ex: NVDA, MC.PA, MSFT)", "AAPL").upper()

if st.button("Lancer l'Analyse"):
    with st.spinner("Récupération des données..."):
        hist, m = fetch_all_data(ticker)
        
    if hist is not None:
        df_reg, sigma, r2 = calculate_log_regression(hist)
        current_p = m["Prix Actuel"]
        reg_p = df_reg['Reg_Price'].iloc[-1]
        dist_reg = ((current_p - reg_p) / reg_p) * 100

        # --- 1. ENTETE & METRIQUES ABSOLUES ---
        st.header(f"{m['Nom']} | {m['Secteur']}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Prix Actuel", f"{current_p:.2f} $")
        c2.metric("Market Cap", format_val(m["Market Cap"]))
        c3.metric("Chiffre d'Affaires", format_val(m["Revenue TTM"]))
        c4.metric("Résultat Net", format_val(m["Net Income TTM"]))

        # --- 2. RATIOS & PERFORMANCE ---
        st.subheader("📊 Ratios de Valorisation & Rentabilité")
        colA, colB, colC = st.columns(3)
        with colA:
            st.write("**Valorisation**")
            st.write(f"• PER Actuel : `{m['PER Trailing']:.2f}`" if m['PER Trailing'] else "• PER Actuel : N/A")
            st.write(f"• PER Futur : `{m['PER Forward']:.2f}`" if m['PER Forward'] else "• PER Futur : N/A")
            st.write(f"• Price / Sales : `{m['P/S Ratio']:.2f}`")
        with colB:
            st.write("**Dividende & Rendement**")
            st.write(f"• Rendement Actuel : `{m['Yield (%)']:.2f}%`")
            st.write(f"• Moyenne 5 Ans : `{m['Yield 5Y Avg']}%`" if m['Yield 5Y Avg'] else "• Moyenne 5 Ans : N/A")
            st.write(f"• Payout Ratio : `{m['Payout Ratio (%)']:.1f}%`")
        with colC:
            st.write("**Efficacité & Dette**")
            st.write(f"• ROE : `{m['ROE (%)']:.2f}%`")
            st.write(f"• Marge Opé. : `{m['Operating Margin (%)']:.2f}%`")
            st.write(f"• Dette / Equity : `{m['Debt/Equity']:.2f}`")

        # --- 3. GRAPHIQUE QUANTITATIF ---
        st.subheader("📉 Croissance Logarithmique & Bandes de Régression")
        
        fig = go.Figure()
        # Bandes 2-Sigma (Extrêmes)
        fig.add_trace(go.Scatter(x=df_reg.index, y=df_reg['Upper_2s'], line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=df_reg.index, y=df_reg['Lower_2s'], fill='tonexty', fillcolor='rgba(255, 0, 0, 0.1)', name="Zone Sous-évaluée (2σ)"))
        # Bandes 1-Sigma
        fig.add_trace(go.Scatter(x=df_reg.index, y=df_reg['Upper_1s'], line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=df_reg.index, y=df_reg['Lower_1s'], fill='tonexty', fillcolor='rgba(0, 255, 0, 0.1)', name="Zone Normale (1σ)"))
        # Prix & Régression
        fig.add_trace(go.Scatter(x=df_reg.index, y=df_reg['Close'], name="Prix Historique", line=dict(color='white', width=1)))
        fig.add_trace(go.Scatter(x=df_reg.index, y=df_reg['Reg_Price'], name="Ligne de Régression", line=dict(color='yellow', dash='dash')))

        fig.update_layout(yaxis_type="log", template="plotly_dark", height=600, 
                          title=f"R² de la tendance : {r2:.2f} | Distance à la moyenne : {dist_reg:.1f}%")
        st.plotly_chart(fig, use_container_width=True)

        # --- 4. ANALYSE IA GEMINI ---
        if api_key:
            with st.spinner("L'IA synthétise les données..."):
                model = genai.GenerativeModel('models/gemini-2.5-flash')
                
                # Prompt ultra-complet incluant toutes les informations extraites
                prompt = f"""
                Analyse {m['Nom']} ({ticker}).
                DONNÉES FINANCIÈRES :
                - PER: {m['PER Trailing']} (Actuel) vs {m['PER Forward']} (Futur).
                - Marges: ROE {m['ROE (%)']:.2f}%, Marge Opé {m['Operating Margin (%)']:.2f}%.
                - Dividende: {m['Yield (%)']:.2f}% (Moyenne 5 ans: {m['Yield 5Y Avg']}%).
                - Dette/Equity: {m['Debt/Equity']}.
                
                DONNÉES QUANTI :
                - Position vs Régression Log: {dist_reg:.1f}%.
                - Support (Plus bas 52 sem): {m['52W Low']}$.
                - Résistance (Plus haut 52 sem): {m['52W High']}$.
                
                CONTEXTE : {m['Summary']}

                MISSIONS :
                1. Analyse la valorisation en croisant PER et distance à la régression.
                2. Juger la rentabilité (ROE/Marges) et la sécurité (Dette).
                3. Comparer le rendement actuel à sa moyenne historique.
                4. Verdict final : "Sous-évalué", "Juste Prix" ou "Surévalué". 
                Réponds en français, avec un ton pro et structuré.
                """
                
                response = model.generate_content(prompt)
                st.subheader("🤖 Diagnostic de l'IA Gemini")
                st.markdown(response.text)
    else:
        st.error("Impossible de récupérer les données pour ce ticker.")

st.caption("Données Yahoo Finance & Analyse Quantitative Scalée. Gemini 2.5 Flash API.")
