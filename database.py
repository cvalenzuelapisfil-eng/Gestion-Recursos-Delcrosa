import psycopg2
import os

def get_connection():
    return psycopg2.connect(
        host=os.environ["SUPABASE_DB_HOST"],
        database=os.environ.get("SUPABASE_DB_NAME", "postgres"),
        user=os.environ["SUPABASE_DB_USER"],
        password=os.environ["SUPABASE_DB_PASSWORD"],
        port=os.environ.get("SUPABASE_DB_PORT", "6543"),
        sslmode="require",
        connect_timeout=10
    )
