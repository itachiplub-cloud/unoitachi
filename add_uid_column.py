from database import get_conn

with get_conn() as conn:
    try:
        conn.execute("ALTER TABLE users ADD COLUMN uid INTEGER;")
        print("âœ… 'uid' column added.")

        conn.execute("UPDATE users SET uid = id;")
        conn.commit()
        print("âœ… 'uid' column populated with existing IDs.")
    except Exception as e:
        print(f"âš ï¸ Error: {e}")
