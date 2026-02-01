from flask import Flask, jsonify, render_template
import psycopg2
import datetime

app = Flask(__name__)

# --- CONFIGURATION ---
RAILWAY_URL = "postgresql://postgres:zMUdeZixVuuoibISeRvqLzZwWxDyVlzs@maglev.proxy.rlwy.net:23110/railway"

# --- DATABASE HELPER ---
def get_db_connection():
    try:
        conn = psycopg2.connect(RAILWAY_URL)
        return conn
    except Exception as e:
        print(f"❌ DB CONNECTION FAILED: {e}")
        return None

# --- WEB ROUTES ---
@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/api/sensor_data")
def get_sensor_data():
    conn = get_db_connection()
    if not conn:
        return jsonify([])

    try:
        cur = conn.cursor()
        
        # 1. Get the last 100 rows, regardless of time
        # We order by ID DESC to get the absolute newest entries
        query = "SELECT id, temperature, humidity, mq2, mq9, mq135, timestamp FROM sensor_data ORDER BY id DESC LIMIT 100"
        
        cur.execute(query)
        rows = cur.fetchall()
        
        # DEBUG: Print to VS Code Terminal
        print(f"🔎 API REQUEST: Found {len(rows)} rows in database.")
        if len(rows) > 0:
            print(f"   Latest Timestamp: {rows[0][6]}")

        # 2. Convert to JSON-friendly format
        data = []
        # În UI.py pe Railway:
        for row in rows:
            data.append({
                "id": row[0],
                "temperature": row[1],
                "humidity": row[2],
                "mq2": row[3],
                "mq9": row[4],
                "mq135": row[5],
                "timestamp": str(row[6]) # Asigură-te că indexul 6 este timestamp-ul
            })

        conn.close()
        return jsonify(data)

    except Exception as e:
        print(f"⚠️ API ERROR: {e}")
        return jsonify([])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

