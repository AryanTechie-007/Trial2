import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "data", "rivallens.db")
conn = sqlite3.connect(db_path)

try:
    conn.execute("ALTER TABLE users ADD COLUMN website_url VARCHAR")
except Exception as e:
    print(f"website_url maybe exists: {e}")

try:
    conn.execute("ALTER TABLE users ADD COLUMN description VARCHAR")
except Exception as e:
    print(f"description maybe exists: {e}")

try:
    conn.execute("UPDATE users SET plan_tier = 'enterprise'")
    conn.commit()
    print("Upgraded everyone to enterprise")
except Exception as e:
    print(f"upgrade failed: {e}")

conn.close()
