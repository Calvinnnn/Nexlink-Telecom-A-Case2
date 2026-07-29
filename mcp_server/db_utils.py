import sqlite3
import os


#for now this file will be used to execute queries to the db, maybe later we can add some other utils

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'nextlink.db')

def execute_query(query: str, params: tuple = (), fetch_one: bool = False):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(query, params)

        if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            conn.commit()
            return {"status": "success", "message": "Database updated successfully."}

        if fetch_one:
            result = cursor.fetchone()
            return dict(result) if result else None
        else:
            return [dict(row) for row in cursor.fetchall()]

    except sqlite3.Error as e:
        return {"error": f"Database error: {str(e)}"}
    finally:
        if 'conn' in locals() and conn:
            conn.close()