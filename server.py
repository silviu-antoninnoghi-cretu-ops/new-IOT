import serial
import threading
import time
from datetime import datetime
import psycopg2

# ================= CONFIGURATION =================
# CHECK YOUR DEVICE MANAGER FOR THESE PORTS
COM_DHT = "COM6"   
COM_MQ  = "COM5"   
BAUD_RATE = 9600
INTERVAL = 10      # Seconds between database inserts

# Database Connection
RAILWAY_URL = "postgresql://postgres:zMUdeZixVuuoibISeRvqLzZwWxDyVlzs@maglev.proxy.rlwy.net:23110/railway"

# Global storage (Thread-safe)
latest_reading = {
    'temperature': 0.0,
    'humidity': 0.0,
    'mq2': 0,
    'mq9': 0,
    'mq135': 0
}

# ================= DATABASE =================
def init_table():
    """Creates the table if it doesn't exist."""
    try:
        conn = psycopg2.connect(RAILWAY_URL)
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS sensor_data (
                    id SERIAL PRIMARY KEY,
                    temperature FLOAT,
                    humidity FLOAT,
                    mq2 INT,
                    mq9 INT,
                    mq135 INT,
                    timestamp TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            conn.commit()
        conn.close()
        print("✅ Database connected. Table ready.")
    except Exception as e:
        print(f"❌ DB Init Error: {e}")

def insert_snapshot():
    """Takes the latest sensor values and saves them to Postgres."""
    # Create snapshot
    snapshot = latest_reading.copy()
    snapshot['timestamp'] = datetime.now()
    
    # Don't save if we only have zeros (prevents filling DB with garbage on startup)
    if snapshot['temperature'] == 0 and snapshot['mq2'] == 0:
        print("⏳ Waiting for valid sensor data before saving...")
        return

    try:
        conn = psycopg2.connect(RAILWAY_URL)
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO sensor_data (temperature, humidity, mq2, mq9, mq135, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                snapshot['temperature'], 
                snapshot['humidity'],
                snapshot['mq2'], 
                snapshot['mq9'], 
                snapshot['mq135'], 
                snapshot['timestamp']
            ))
            conn.commit()
        conn.close()
        
        # Log to console so you know it's working
        t_str = f"{snapshot['temperature']:.1f}°C"
        h_str = f"{snapshot['humidity']:.1f}%"
        gas_str = f"MQ2:{snapshot['mq2']} MQ9:{snapshot['mq9']} MQ135:{snapshot['mq135']}"
        print(f"💾 SAVED: {t_str} | {h_str} | {gas_str}")
        
    except Exception as e:
        print(f"⚠️ Insert Error: {e}")

# ================= SENSORS =================
def read_dht():
    """Reads Temperature & Humidity"""
    try:
        print(f"🔌 Connecting to DHT on {COM_DHT}...")
        arduino = serial.Serial(COM_DHT, BAUD_RATE, timeout=1)
        time.sleep(2)
        print(f"✅ DHT Connected!")
        
        while True:
            if arduino.in_waiting > 0:
                try:
                    line = arduino.readline().decode('utf-8', errors='ignore').strip()
                    # Format: "DHT,24.50,60.10"
                    if line.startswith("DHT"):
                        parts = line.split(",")
                        if len(parts) == 3:
                            t, h = float(parts[1]), float(parts[2])
                            latest_reading['temperature'] = t
                            latest_reading['humidity'] = h
                except ValueError:
                    pass # Ignore bad packets
    except Exception as e:
        print(f"❌ DHT Error ({COM_DHT}): {e}")

def read_mq():
    """Reads Gas Sensors"""
    try:
        print(f"🔌 Connecting to MQ on {COM_MQ}...")
        arduino = serial.Serial(COM_MQ, BAUD_RATE, timeout=1)
        time.sleep(2)
        print(f"✅ MQ Connected!")
        
        while True:
            if arduino.in_waiting > 0:
                try:
                    line = arduino.readline().decode('utf-8', errors='ignore').strip()
                    # Format: "MQ,200,150,300"
                    if line.startswith("MQ"):
                        parts = line.split(",")
                        if len(parts) == 4:
                            latest_reading['mq2'] = int(parts[1])
                            latest_reading['mq9'] = int(parts[2])
                            latest_reading['mq135'] = int(parts[3])
                except ValueError:
                    pass
    except Exception as e:
        print(f"❌ MQ Error ({COM_MQ}): {e}")

# ================= MAIN =================
if __name__ == "__main__":
    init_table()
    
    # Start Sensors in Background
    t1 = threading.Thread(target=read_dht, daemon=True)
    t2 = threading.Thread(target=read_mq, daemon=True)
    t1.start()
    t2.start()
    
    print(f"--- BRIDGE RUNNING (Saving every {INTERVAL}s) ---")
    
    try:
        while True:
            time.sleep(INTERVAL)
            insert_snapshot()
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")