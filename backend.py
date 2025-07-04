# pipeline.py

import os
import json
import sqlite3
import pandas as pd
import psycopg
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 1) Collecte des données Bluesky
#from test_getall_data import search_bluesky_posts

# 2) Détection Fake News
#from test_bert_finet_final import predict_tweet

# 3) Analyse émotionnelle
#from test import predict_sentiment

# 4) Score de fiabilité
#from scorefiab import compute_reliability, predict_sentiment


def main():
    from test_getall_data import search_bluesky_posts
    from test_bert_finet_final import predict_tweet
    from scorefiab import compute_reliability, predict_sentiment
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
    step2_path = "data/bluesky_posts_step2.csv" ##iidfbszi 
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

#     # ─── Étape 5 : Création/Mise à jour de la BDD SQLite ───
#     print("💾 Mise à jour de la base SQLite…")
#     conn = sqlite3.connect("data/tweets_analysis.db")
#     df.to_sql("posts", conn, if_exists="replace", index=False)
#    # 5.2 analysis (tes colonnes d'analyse regroupées)
#     df[[
#         "post_uri",
#         "fake_news_label",
#         "fake_news_probs",
#         "top_emotion",
#         "reliability_score"
#     ]].to_sql("analysis", conn, if_exists="replace", index=False)


#     conn.close()
#     print("✅ Base SQLite à jour : data/tweets_analysis.db")


    print("💾 Mise à jour de la base PostgreSQL…")

    # Connexion à PostgreSQL (Neon)
    # pg_conn = psycopg.connect(
    #     host=os.environ["PG_HOST"],
    #     dbname=os.environ["PG_DB"],
    #     user=os.environ["PG_USER"],
    #     password=os.environ["PG_PASS"],
    #     port=5432,
    #     sslmode="require"
    # )
    # pg_cursor = pg_conn.cursor()
    
    pg_conn = psycopg.connect(
        host="ep-purple-bird-a23zswcw-pooler.eu-central-1.aws.neon.tech",
        dbname="analyse_tweet_db",
        user="neondb_owner",
        password="npg_tl7cKYQdWLe6",
        port=5432,
        sslmode="require"
    )

    pg_cursor = pg_conn.cursor()
    
    # Créer les tables si elles n'existent pas
    pg_cursor.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        post_uri TEXT PRIMARY KEY,
        text TEXT
    )
    """)

    pg_cursor.execute("""
    CREATE TABLE IF NOT EXISTS analysis (
        post_uri TEXT PRIMARY KEY,
        fake_news_label TEXT,
        fake_news_probs TEXT,
        top_emotion TEXT,
        reliability_score INTEGER,
        FOREIGN KEY (post_uri) REFERENCES posts(post_uri)
    )
    """)
    pg_conn.commit()

    # Insertion / Mise à jour dans PostgreSQL
    for _, row in df.iterrows():
        pg_cursor.execute("""
            INSERT INTO posts (post_uri, text)
            VALUES (%s, %s)
            ON CONFLICT (post_uri) DO UPDATE SET text = EXCLUDED.text
        """, (row["post_uri"], row["text"]))

        pg_cursor.execute("""
            INSERT INTO analysis (post_uri, fake_news_label, fake_news_probs, top_emotion, reliability_score)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (post_uri) DO UPDATE SET 
                fake_news_label = EXCLUDED.fake_news_label,
                fake_news_probs = EXCLUDED.fake_news_probs,
                top_emotion = EXCLUDED.top_emotion,
                reliability_score = EXCLUDED.reliability_score
        """, (
            row["post_uri"],
            row["fake_news_label"],
            row["fake_news_probs"],
            row["top_emotion"],
            int(row["reliability_score"])
        ))

    pg_conn.commit()
    pg_cursor.close()
    pg_conn.close()
    print("✅ PostgreSQL à jour !")


def get_results_from_postgres() -> pd.DataFrame:
    # pg_conn = psycopg.connect(
    #     host=os.environ["PG_HOST"],
    #     dbname=os.environ["PG_DB"],
    #     user=os.environ["PG_USER"],
    #     password=os.environ["PG_PASS"],
    #     port=5432,
    #     sslmode="require"
    # )
    pg_conn = psycopg.connect(
        host="ep-purple-bird-a23zswcw-pooler.eu-central-1.aws.neon.tech",
        dbname="analyse_tweet_db",
        user="neondb_owner",
        password="npg_tl7cKYQdWLe6",
        port=5432,
        sslmode="require"
    )

    query = """
    SELECT
    p.post_uri,
    p.text,
    a.fake_news_label,
    a.fake_news_probs,
    a.top_emotion,
    a.reliability_score
    FROM posts AS p
    JOIN analysis AS a USING(post_uri)
    """
    
    df = pd.read_sql(query, pg_conn)
    pg_conn.close()
    return df


if __name__ == "__main__":
    main()
