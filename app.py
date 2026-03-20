import streamlit as st
import yfinance as yf
import pandas as pd

@st.cache_data(ttl=3600)
def get_advanced_stock_data(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)
    info = stock.info
    
    # 1. Données Absolues & Ratios Actuels
    metrics = {
        "Nom": info.get("longName", "N/A"),
        "Prix": info.get("currentPrice"),
        "Market Cap": info.get("marketCap"),
        "Revenue (TTM)": info.get("totalRevenue"),
        "Net Income (TTM)": info.get("netIncomeToCommon"),
        "PER Actuel": info.get("trailingPE"),
        "Forward PER": info.get("forwardPE"),
        "P/S Ratio": info.get("priceToSalesTrailing12Months"),
        "Div Yield %": info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0,
        "ROE": info.get("returnOnEquity", 0) * 100 if info.get("returnOnEquity") else 0,
        "Dette/Equity": info.get("debtToEquity"),
        "Marge Opérationnelle": info.get("operatingMargins", 0) * 100 if info.get("operatingMargins") else 0,
    }

    # 2. Récupération des moyennes historiques (5 ans)
    # yfinance fournit souvent la moyenne du dividende sur 5 ans directement
    metrics["Div Yield 5Y Avg"] = info.get("fiveYearAvgDividendYield", "N/A")
    
    # Calcul manuel du PER moyen sur 5 ans (approximation via historique)
    try:
        hist = stock.history(period="5y")
        # On simplifie : Prix moyen annuel / EPS moyen annuel (si dispo)
        # Note: Pour un PER historique précis, il faut croiser prix et bénéfices passés
        # Ici on utilise la donnée 'trailingPegRatio' ou on affiche le PER moyen secteur si dispo
        metrics["PER 5Y Avg"] = "Calcul en cours..." # Placeholder pour logique complexe
    except:
        metrics["PER 5Y Avg"] = "N/A"

    return metrics, info

def format_large_number(num):
    if num is None: return "N/A"
    if num >= 1e12: return f"{num / 1e12:.2f} T"
    if num >= 1e9: return f"{num / 1e9:.2f} Md"
    if num >= 1e6: return f"{num / 1e6:.2f} M"
    return str(num)

# --- Interface Streamlit ---
st.title("🔬 Analyse Fondamentale Avancée")

ticker_input = st.text_input("Ticker", "AAPL").upper()

if st.button("Extraire les Ratios"):
    data, raw_info = get_advanced_stock_data(ticker_input)
    
    st.header(f"{data['Nom']} ({ticker_input})")
    
    # --- SECTION 1 : VALEURS ABSOLUES ---
    st.subheader("📊 Valeurs Absolues (TTM)")
    c1, c2, c3 = st.columns(3)
    c1.metric("Market Cap", format_large_number(data['Market Cap']))
    c2.metric("Chiffre d'Affaires", format_large_number(data['Revenue (TTM)']))
    c3.metric("Résultat Net", format_large_number(data['Net Income (TTM)']))

    st.divider()

    # --- SECTION 2 : RATIOS DE VALORISATION vs HISTORIQUE ---
    st.subheader("⚖️ Valorisation & Ratios")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.write("**Ratios de Prix**")
        per_hist = data["PER 5Y Avg"]
        st.write(f"• **PER Actuel :** {data['PER Actuel']:.2f}")
        st.write(f"• **Forward PER :** {data['Forward PER']:.2f}")
        st.write(f"• **P/S Ratio :** {data['P/S Ratio']:.2f}")
        
    with col_b:
        st.write("**Rendement & Santé**")
        current_yield = data['Div Yield %']
        avg_yield = data['Div Yield 5Y Avg']
        st.write(f"• **Rendement Actuel :** {current_yield:.2f}%")
        st.write(f"• **Moyenne 5 ans :** {avg_yield}%")
        
        # Petit indicateur visuel
        if isinstance(avg_yield, (int, float)) and current_yield > avg_yield:
            st.success("Le rendement actuel est supérieur à sa moyenne 5 ans.")
        elif isinstance(avg_yield, (int, float)):
            st.warning("Le rendement actuel est inférieur à sa moyenne 5 ans.")

    st.divider()

    # --- SECTION 3 : EFFICACITÉ ---
    st.subheader("🏗️ Rentabilité & Solidité")
    col_x, col_y, col_z = st.columns(3)
    col_x.metric("ROE (Rentabilité)", f"{data['ROE']:.2f}%")
    col_y.metric("Marge Opé.", f"{data['Marge Opérationnelle']:.2f}%")
    col_z.metric("Dette / Equity", f"{data['Dette/Equity']:.2f}" if data['Dette/Equity'] else "N/A")

    # Affichage du résumé business pour contexte
    with st.expander("Voir le descriptif de l'entreprise"):
        st.write(raw_info.get("longBusinessSummary"))
