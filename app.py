import streamlit as st
import google.generativeai as genai

st.title("🛠 Diagnostic Gemini")

# Saisie de la clé
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Clé API Gemini :", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
        
        # Étape 1 : Lister les modèles disponibles pour TA clé
        st.write("### Modèles accessibles avec votre clé :")
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        if available_models:
            st.success(f"Connexion réussie ! Modèles trouvés : {available_models}")
            
            # Étape 2 : Test de génération avec le premier modèle de la liste
            selected_model = st.selectbox("Choisissez un modèle pour tester :", available_models)
            ticker = st.text_input("Ticker pour le test (ex: AAPL) :", "AAPL")
            
            if st.button("Tester la génération"):
                model = genai.GenerativeModel(selected_model)
                response = model.generate_content(f"Donne-moi une info courte sur {ticker}")
                st.write(response.text)
        else:
            st.warning("La clé est valide mais aucun modèle n'est listé. Vérifiez vos permissions sur Google AI Studio.")

    except Exception as e:
        st.error(f"Erreur de connexion : {e}")
else:
    st.info("Veuillez entrer votre clé API pour tester.")
