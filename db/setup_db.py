import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, 'nexlink.db')
SCHEMA_PATH = os.path.join(BASE_DIR, 'schema.sql')
SEED_PATH = os.path.join(BASE_DIR, 'seed.sql')

def reset_database():

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Existing database deleted.")
    else:
        print("No existing database found. Creating a new one...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        with open(SCHEMA_PATH, 'r') as schema_file:
            print("Apply schema")
            cursor.executescript(schema_file.read())

        with open(SEED_PATH, 'r') as seed_file:
            print("Applying seed data")
            cursor.executescript(seed_file.read())

        conn.commit()
        print("Success: Nextink database rebuilt and seeded perfectly.")

    except FileNotFoundError as e:
        print(f"Error: Missing SQL file. Ensure both schema.sql and seed.sql are in the same folder. ({e})")
    except sqlite3.Error as e:
        print(f"Database Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    reset_database()