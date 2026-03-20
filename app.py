import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats
import google.generativeai as genai

# --- Configuration ---
st.set_page_config(page_title="Quant Analysis & IA", layout="wide")

if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Clé API Gemini :", type="password")

if api_key:
    genai.configure(api_key=api_key)

# --- Fonctions de Calcul ---
@st.cache_data(ttl=3600)
def get_extended_data(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)
    
    # 1. Historique long terme (depuis 2000)
    df = stock.history(start="2000-01-01")
    if df.empty: return None, None, None
    
    # 2. Ratios fondamentaux
    info = stock.info
    metrics = {
        "name": info.get("longName"),
        "per": info.get("trailingPE"),
        "forward_per": info.get("forwardPE"),
        "yield": (info.get("dividendYield") or 0) * 100,
        "yield_5y": info.get("fiveYearAvgDividendYield") or "N/A",
        "debt_equity": info.get("debtToEquity"),
        "roe": (info.get("returnOnEquity") or 0) * 100,
        "high_52": info.get("fiftyTwoWeekHigh"),
        "low_52": info.get("fiftyTwoWeekLow"),
    }
    return df, metrics, info

def calculate_regression(df):
    # Travail sur l'échelle Log
    df = df.copy()
    df['Log_Price'] = np.log(df['Close'])
    df['Time_Index'] = np.arange(len(df))
    
    # Régression linéaire : Log(P) = m * Time + b
    slope, intercept, r_value, p_value, std_err = stats.linregress(df['Time_Index'], df['Log_Price'])
    
    df['Regression'] = intercept + slope * df['Time_Index']
    
    # Calcul des Bandes (Sigma)
    residuals = df['Log_Price'] - df['Regression']
    std_dev = np.std(residuals)
    
    df['Upper_1s'] = df['Regression'] + std_dev
    df['Lower_1s'] = df['Regression'] - std_dev
    df['Upper_2s'] = df['Regression'] + 2 * std_dev
    df['Lower_2s'] = df['Regression'] - 2 * std_dev
    
    # Repasser en échelle normale pour le graphique
    for col in ['Regression', 'Upper_1s', 'Lower_1s', 'Upper_2s', 'Lower_2s']:
        df[col] = np.exp(df[col])
        
    return df, std_dev, r_value**2

# --- Interface ---
st.title("📈 Analyse Quantitative & IA Stratégique")
ticker = st.text_input("Ticker", "AAPL").upper()

if st.button("Lancer l'Analyse"):
    df, metrics, raw_info = get_extended_data(ticker)
    
    if df is not None:
        # 1. Calculs Quants
        df_reg, sigma, r_squared = calculate_regression(df)
        current_price = df_reg['Close'].iloc[-1]
        reg_price = df_reg['Regression'].iloc[-1]
        dist_reg = ((current_price - reg_price) / reg_price) * 100
        
        # 2. Affichage des Ratios
        st.subheader(f"📊 Ratios Fondamentaux - {metrics['name']}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Prix Actuel", f"{current_price:.2f} $")
        c2.metric("PER (TTM)", f"{metrics['per']:.2f}" if metrics['per'] else "N/A")
        c3.metric("Rendement", f"{metrics['yield']:.2f} %")
        c4.metric("Position / Régression", f"{dist_reg:.1f} %")

        # 3. Graphique Logarithmique
        fig = go.Figure()
        # Bandes 2-Sigma (Zone d'extrême)
        fig.add_trace(go.Scatter(x=df_reg.index, y=df_reg['Upper_2s'], line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=df_reg.index, y=df_reg['Lower_2s'], fill='tonexty', fillcolor='rgba(255, 0, 0, 0.1)', name="Zone 2-Sigma", line=dict(width=0)))
        
        # Bandes 1-Sigma (Zone normale)
        fig.add_trace(go.Scatter(x=df_reg.index, y=df_reg['Upper_1s'], line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=df_reg.index, y=df_reg['Lower_1s'], fill='tonexty', fillcolor='rgba(0, 255, 0, 0.1)', name="Zone 1-Sigma", line=dict(width=0)))

        # Prix et Régression
        fig.add_trace(go.Scatter(x=df_reg.index, y=df_reg['Close'], name="Prix", line=dict(color='white', width=1.5)))
        fig.add_trace(go.Scatter(x=df_reg.index, y=df_reg['Regression'], name="Régression (Moyenne)", line=dict(color='yellow', dash='dash')))

        fig.update_layout(yaxis_type="log", template="plotly_dark", height=600, title=f"Courbe de Croissance Logarithmique - R²: {r_squared:.2f}")
        st.plotly_chart(fig, use_container_width=True)

        # 4. Analyse IA
        with st.spinner("Analyse contextuelle par Gemini..."):
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            prompt = f"""
            Analyse {ticker} avec ces données :
            - Prix : {current_price:.2f}$ (vs 52w High: {metrics['high_52']}, Low: {metrics['low_52']})
            - PER Actuel: {metrics['per']}, Forward: {metrics['forward_per']}
            - Stats Régression : Le prix est à {dist_reg:.1f}% de sa droite de tendance historique (échelle log).
            - Qualité : ROE {metrics['roe']:.2f}%, Dette/Equity {metrics['debt_equity']}.
            
            Instructions :
            1. Dis si l'action est statistiquement chère (ex: au-dessus de +1 sigma) ou bon marché.
            2. Identifie les supports techniques (Low 52w ou ligne de régression) et résistances.
            3. Verdict final sur la valorisation.
            Réponds en français de façon concise.
            """
            response = model.generate_content(prompt)
            st.subheader("🤖 Verdict de l'IA")
            st.markdown(response.text)
