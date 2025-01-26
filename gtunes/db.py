import sqlite3
import os

conn = None

def load_db():
    global conn
    db_path = os.getenv("TUNE_DB", "example.db")
    conn = sqlite3.connect(db_path)
    return conn.cursor()

def close_db():
    global conn
    # Commit the changes and close the connection
    conn.commit()
    conn.close()

def init_tune_db(cursor):
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tunes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        status INTEGER,
        type TEXT,
        tune_key TEXT,
        abc TEXT,
        comments TEXT,
        recordings TEXT
    )
    ''')

def add_tune(id="", name="", type_="", key="", abc="", recordings=""):
    cursor = load_db()

    init_tune_db(cursor)

    # Insert data into the users table
    cursor.execute('''
    INSERT INTO tunes (name, type) VALUES (?, ?)
    ''', (name, type_))

    close_db()

def list_tunes():
    cursor = load_db()

    # Query the database
    cursor.execute('SELECT * FROM tunes')

    # Fetch all rows from the result of the query
    rows = cursor.fetchall()

    # Iterate through the results and print each row
    for row in rows:
        print(row)

    close_db()

if __name__ == "__main__":
    add_tune(name="Lark in the Morning", key="D", type_="jig")
    list_tunes()
