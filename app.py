# # app.py

# import streamlit as st
# import pandas as pd
# import sqlite3
# import subprocess
# import sys
# import os

# # ────────────────
# # 0) Chemin vers ton dossier "profil_rouge" où se trouve pipeline.py
# BASE_DIR     = os.path.dirname(__file__)                     # ex: .../interface-web
# PIPELINE_DIR = os.path.abspath(os.path.join(BASE_DIR))



# # ────────────────

# @st.cache_data(show_spinner=False)
# def run_backend():
#     """
#     Exécute pipeline.py depuis le bon dossier pour régénérer
#     data/tweets_analysis.db (et les CSV si tu en produis).
#     """
#     subprocess.run(
#         [sys.executable, "backend.py"],
#         cwd=PIPELINE_DIR,
#         check=True
#     )
#     return

# # 1) Config page
# st.set_page_config(page_title="Dashboard Tweets Bluesky", layout="wide")

# # 2) Lance la pipeline pour (re)construire la BDD
# run_backend()

# # 3) Connexion SQLite
# DB_PATH = os.path.join(PIPELINE_DIR, "data", "tweets_analysis.db")
# conn    = sqlite3.connect(DB_PATH)

# # 4) Charger les données de la BDD
# @st.cache_data
# def load_data():
#     query = """
#     SELECT
#       p.post_uri,
#       p.text,
#       a.fake_news_label,
#       a.fake_news_probs,
#       a.top_emotion,
#       a.reliability_score
#     FROM posts AS p
#     JOIN analysis AS a USING(post_uri)
#     """
#     return pd.read_sql(query, conn)

# df = load_data()

# # 5) Sidebar – filtres
# st.sidebar.header("🎯 Filtres")

# min_score = st.sidebar.slider("Score de fiabilité minimum (%)", 0, 100, 0)
# emotions  = st.sidebar.multiselect(
#     "Émotion détectée",
#     options=df["top_emotion"].unique(),
#     default=df["top_emotion"].unique()
# )
# fake_opt = st.sidebar.selectbox("Fake news ?", ["Tous", "Vrai", "Faux"])

# search_txt = st.sidebar.text_input("🔍 URL ou mot-clé")

# # 6) Application des filtres
# df_f = df[
#     (df["reliability_score"] >= min_score) &
#     (df["top_emotion"].isin(emotions))
# ]
# if fake_opt != "Tous":
#     df_f = df_f[df_f["fake_news_label"] == fake_opt]

# if search_txt:
#     mask_uri  = df_f["post_uri"].str.contains(search_txt, na=False)
#     mask_text = df_f["text"].str.contains(search_txt, na=False, case=False)
#     df_f = df_f[mask_uri | mask_text]

# # 7) Affichage principal
# st.markdown("## 🧠 Tableau de bord - Analyse des Tweets")
# st.markdown("### 📋 Tweets filtrés")
# st.dataframe(
#     df_f[["text", "reliability_score", "top_emotion", "fake_news_label"]],
#     use_container_width=True
# )

# # 8) Graphiques
# st.markdown("### 📊 Distribution des scores de fiabilité")
# hist = df_f["reliability_score"]
# st.bar_chart(hist.value_counts(bins=10).sort_index())

# st.markdown("### 🥧 Répartition Fake vs Vrai")
# pie = df_f["fake_news_label"].value_counts()
# st.pyplot(
#     pie.plot.pie(
#         autopct="%.1f%%",
#         title="Fake news ?"
#     ).figure
# )

# # 9) Détail si un seul résultat
# if search_txt and len(df_f) == 1:
#     row = df_f.iloc[0]
#     st.markdown("---")
#     st.markdown("### Détail pour ce tweet")
#     st.write(f"**URL :** {row.post_uri}")
#     st.write(f"**Texte :** {row.text}")
#     st.write(f"**Fake news ?** {row.fake_news_label}")
#     st.write(f"**Émotion :** {row.top_emotion}")
#     st.write(f"**Fiabilité :** {row.reliability_score}%")

# conn.close()


# # import streamlit as st
# # import pandas as pd
# # import os
# # from backend import get_results_from_postgres  # ✅ Ajouté

# # # 1) Config page
# # st.set_page_config(page_title="Dashboard Tweets Bluesky", layout="wide")

# # # 2) Charger les données depuis PostgreSQL
# # @st.cache_data
# # def load_data():
# #     return get_results_from_postgres()

# # df = load_data()

from flask import Flask, render_template, request
import pandas as pd
import os
from backend import main as run_pipeline
from backend import get_results_from_postgres

app = Flask(__name__)

@app.route("/")
def index():
    try:
        # 1. Exécuter la pipeline
        run_pipeline()
        
        # 2. Charger les résultats depuis PostgreSQL
        df = get_results_from_postgres()

        # 3. Appliquer les filtres (optionnels via paramètres GET)
        min_score = int(request.args.get("min_score", 0))
        fake_filter = request.args.get("fake_news", "Tous")
        emotion_filter = request.args.getlist("emotion")

        df_f = df[df["reliability_score"] >= min_score]

        if fake_filter != "Tous":
            df_f = df_f[df_f["fake_news_label"] == fake_filter]

        if emotion_filter:
            df_f = df_f[df_f["top_emotion"].isin(emotion_filter)]

        return render_template("dashboard.html", data=df_f.to_dict(orient="records"))
 
    except Exception as e:
        return f"Une erreur est survenue : {e}", 500

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))  # Render te donne PORT en env var
    app.run(host="0.0.0.0", port=port)  #modif

