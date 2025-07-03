# pipeline.py

import os
import json
import sqlite3
import pandas as pd

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 1) Collecte des données Bluesky
from test_getall_data import search_bluesky_posts

# 2) Détection Fake News
from test_bert_finet_final import predict_tweet

# 3) Analyse émotionnelle
#from test import predict_sentiment

# 4) Score de fiabilité
from scorefiab import compute_reliability, predict_sentiment


def main():
    # ─── Étape 1 : Collecte et préparation ───
    print("🔍 Récupération des posts Bluesky…")
    posts = search_bluesky_posts(query="political", limit=200, lang="en")
    df = pd.DataFrame(posts)

    # Assure-toi que le répertoire data/ existe
    os.makedirs("data", exist_ok=True)

    # Convertir la colonne `labels` en JSON-string (pour éviter les problèmes de sérialisation)
    df['labels'] = df['labels'].apply(lambda x: json.dumps(x, default=str))

    # ─── Étape 2 : Détection des Fake News ───
    print("🚨 Détection des fake news…")
    fake_results = df['text'].apply(predict_tweet)
    df['fake_news_label'] = fake_results.apply(lambda res: res[0])
    df['fake_news_probs'] = fake_results.apply(lambda res: json.dumps(res[1].tolist()))
    step2_path = "data/bluesky_posts_step2.csv"
    df.to_csv(step2_path, index=False, encoding="utf-8-sig")
    print(f"✅ Étape 2 terminée → {step2_path}")

    # ─── Étape 3 : Analyse émotionnelle ───
    print("😊 Analyse émotionnelle…")
    emos = df['text'].apply(predict_sentiment)
    df['emotions_raw'] = emos.apply(lambda lst: json.dumps(lst))
    def top_label(scores):
        best = max(scores, key=lambda x: x['score'])
        return best['label']
    df['top_emotion'] = emos.apply(top_label)
    step3_path = "data/bluesky_posts_step3.csv"
    df.to_csv(step3_path, index=False, encoding="utf-8-sig")
    print(f"✅ Étape 3 terminée → {step3_path}")

    # ─── Étape 4 : Score de fiabilité ───
    print("🔢 Calcul du score de fiabilité…")
    df = compute_reliability(df)
    step4_path = "data/bluesky_posts_step4.csv"
    df.to_csv(step4_path, index=False, encoding="utf-8-sig")
    print(f"✅ Étape 4 terminée → {step4_path}")

    # ─── Étape 5 : Création/Mise à jour de la BDD SQLite ───
    print("💾 Mise à jour de la base SQLite…")
    conn = sqlite3.connect("data/tweets_analysis.db")
    df.to_sql("posts", conn, if_exists="replace", index=False)
   # 5.2 analysis (tes colonnes d'analyse regroupées)
    df[[
        "post_uri",
        "fake_news_label",
        "fake_news_probs",
        "top_emotion",
        "reliability_score"
    ]].to_sql("analysis", conn, if_exists="replace", index=False)


    conn.close()
    print("✅ Base SQLite à jour : data/tweets_analysis.db")


if __name__ == "__main__":
    main()
