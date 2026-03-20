import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats
import google.generativeai as genai
from datetime import datetime

# --- Configuration ---
st.set_page_config(page_title="Terminal Quant Expert", layout="wide")

if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Clé API Gemini :", type="password")

if api_key:
    genai.configure(api_key=api_key)

@st.cache_data(ttl=3600)
def get_stock_full_package(ticker):
    stock = yf.Ticker(ticker)
    df = stock.history(start="2000-01-01")
    info = stock.info
    return df, info

def calculate_quant_metrics(df_full, start_date, end_date):
    # Filtrage pour le calcul de la régression uniquement
    mask = (df_full.index.date >= start_date) & (df_full.index.date <= end_date)
    df_calc = df_full.loc[mask].copy()
    
    if len(df_calc) < 10: return None
    
    # Régression Log
    df_calc['Log_P'] = np.log(df_calc['Close'])
    df_calc['Index'] = np.arange(len(df_calc))
    slope, intercept, r_val, p_val, std_err = stats.linregress(df_calc['Index'], df_calc['Log_P'])
    
    # Calcul sur TOUT le dataframe pour affichage continu
    df_full = df_full.copy()
    # On recalcule l'index temporel basé sur le point de départ de la sélection
    base_idx = df_full.index.get_loc(df_calc.index[0])
    df_full['Global_Index'] = np.arange(len(df_full)) - base_idx
    
    df_full['Reg_Log'] = intercept + slope * df_full['Global_Index']
    residuals = df_calc['Log_P'] - (intercept + slope * np.arange(len(df_calc)))
    std_dev = np.std(residuals)
    
    # Transformation inverse (Exp)
    df_full['Reg_P'] = np.exp(df_full['Reg_Log'])
    df_full['U1'] = np.exp(df_full['Reg_Log'] + std_dev)
    df_full['L1'] = np.exp(df_full['Reg_Log'] - std_dev)
    df_full['U2'] = np.exp(df_full['Reg_Log'] + 2 * std_dev)
    df_full['L2'] = np.exp(df_full['Reg_Log'] - 2 * std_dev)
    
    return df_full, r_val**2, std_dev

# --- UI ---
st.title("📈 Analyseur Quantitatif de Précision")

col_input, col_dates = st.columns([1, 2])
with col_input:
    ticker = st.text_input("Ticker", "AAPL").upper()
with col_dates:
    # Curseur de date pour la régression
    start_date_reg = st.slider("Période de calcul de la régression", 
                              min_value=datetime(2000, 1, 1).date(), 
                              max_value=datetime.now().date(),
                              value=(datetime(2015, 1, 1).date(), datetime.now().date()))

if st.button("Analyser"):
    df, info = get_stock_full_package(ticker)
    
    if not df.empty:
        # Calculs
        df_res, r2, sigma_val = calculate_quant_metrics(df, start_date_reg[0], start_date_reg[1])
        
        # --- 1. AFFICHAGE DES RATIOS ---
        st.subheader(f"📊 Données Fondamentales - {info.get('longName')}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Prix", f"{df['Close'].iloc[-1]:.2f} $")
        m2.metric("PER (TTM)", f"{info.get('trailingPE'):.2f}" if info.get('trailingPE') else "N/A")
        m3.metric("ROE", f"{info.get('returnOnEquity', 0)*100:.1f}%")
        m4.metric("Dette/Equity", f"{info.get('debtToEquity'):.2f}" if info.get('debtToEquity') else "N/A")

        # --- 2. GRAPHIQUE ---
        fig = go.Figure()
        
        # Bandes Sigma (très transparentes)
        fig.add_trace(go.Scatter(x=df_res.index, y=df_res['U2'], line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=df_res.index, y=df_res['L2'], fill='tonexty', fillcolor='rgba(255, 0, 0, 0.05)', name="Extrême (2σ)"))
        
        fig.add_trace(go.Scatter(x=df_res.index, y=df_res['U1'], line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=df_res.index, y=df_res['L1'], fill='tonexty', fillcolor='rgba(0, 255, 0, 0.05)', name="Normal (1σ)"))

        # Prix (Blanc vif et épais)
        fig.add_trace(go.Scatter(x=df_res.index, y=df_res['Close'], name="Prix", line=dict(color='white', width=2.5)))
        
        # Régression (Jaune pointillé)
        fig.add_trace(go.Scatter(x=df_res.index, y=df_res['Reg_P'], name="Tendance", line=dict(color='yellow', dash='dot', width=1.5)))

        fig.update_layout(yaxis_type="log", template="plotly_dark", height=600, 
                          title=f"Régression calculée du {start_date_reg[0]} au {start_date_reg[1]} (R²: {r2:.2f})")
        st.plotly_chart(fig, use_container_width=True)

        # --- 3. ANALYSE IA ---
        if api_key:
            with st.spinner("Analyse Gemini en cours..."):
                current_p = df['Close'].iloc[-1]
                target_p = df_res['Reg_P'].iloc[-1]
                dist = ((current_p - target_p) / target_p) * 100
                
                model = genai.GenerativeModel('models/gemini-2.5-flash')
                prompt = f"""
                Analyse {ticker} avec :
                - PER: {info.get('trailingPE')}, Forward PER: {info.get('forwardPE')}
                - Rentabilité: ROE {info.get('returnOnEquity', 0)*100:.2f}%, Marge {info.get('operatingMargins', 0)*100:.2f}%
                - Dette/Equity: {info.get('debtToEquity')}
                - Quanti: Le prix est à {dist:.1f}% de sa droite de régression log calculée sur la période {start_date_reg}.
                
                Donne un verdict sur la valorisation (sous/sur-évalué) et identifie les supports/résistances visibles sur le graphique.
                """
                response = model.generate_content(prompt)
                st.subheader("🤖 Analyse Stratégique")
                st.markdown(response.text)
