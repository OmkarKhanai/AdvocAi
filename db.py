import sqlite3

def create_db():
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY,
            username TEXT,
            role TEXT,
            content TEXT
        )
    ''')

    # Check if the profile_image column exists, and add it if it doesn't
    c.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in c.fetchall()]
    if 'profile_image' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN profile_image TEXT")
    
    conn.commit()
    conn.close()

def add_user(username, password, profile_image):
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, profile_image) VALUES (?, ?, ?)", (username, password, profile_image))
        conn.commit()
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
    return True

def get_user(username, password):
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = c.fetchone()
    conn.close()
    if user:
        return {"username": user[1], "profile_image": user[3]}
    return None

def add_chat(username, role, content):
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    c.execute("INSERT INTO chat_history (username, role, content) VALUES (?, ?, ?)", (username, role, content))
    conn.commit()
    conn.close()

def get_chat_history(username):
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    c.execute("SELECT role, content FROM chat_history WHERE username=?", (username,))
    history = c.fetchall()
    conn.close()
    return history

def clear_chat_history(username):
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    c.execute("DELETE FROM chat_history WHERE username=?", (username,))
    conn.commit()
    conn.close()
