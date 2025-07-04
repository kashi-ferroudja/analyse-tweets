import sqlite3
import psycopg
import pandas as pd

# --- 1. Connexion à SQLite
sqlite_path = "data/tweets_analysis.db"
sqlite_conn = sqlite3.connect(sqlite_path)

# Lire les données
df_posts = pd.read_sql("SELECT * FROM posts", sqlite_conn)
df_analysis = pd.read_sql("SELECT * FROM analysis", sqlite_conn)

sqlite_conn.close()

# --- 2. Connexion à PostgreSQL (Neon) — identifiants en dur
pg_conn = psycopg.connect(
    host="ep-purple-bird-a23zswcw-pooler.eu-central-1.aws.neon.tech",
    dbname="analyse_tweet_db",
    user="neondb_owner",
    password="npg_tl7cKYQdWLe6",
    port=5432,
    sslmode="require"
)

pg_cursor = pg_conn.cursor()

# --- 3. Créer les tables si elles n'existent pas
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

# --- 4. Insérer les données dans PostgreSQL

for _, row in df_posts.iterrows():
    pg_cursor.execute("""
    INSERT INTO posts (post_uri, text)
    VALUES (%s, %s)
    ON CONFLICT (post_uri) DO NOTHING
    """, (row["post_uri"], row["text"]))

for _, row in df_analysis.iterrows():
    pg_cursor.execute("""
    INSERT INTO analysis (post_uri, fake_news_label, fake_news_probs, top_emotion, reliability_score)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (post_uri) DO NOTHING
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

print("✅ Migration terminée avec succès.")
