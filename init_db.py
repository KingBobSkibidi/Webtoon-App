import sqlite3

conn = sqlite3.connect('webtoons.db')

c = conn.cursor()

# enable foreign keys
c.execute("PRAGMA foreign_keys = ON;")

# drop the old webtoons table if it exists
c.execute("DROP TABLE IF EXISTS webtoons;")

# webtoon table
c.execute('''
CREATE TABLE IF NOT EXISTS webtoons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    chapter INTEGER DEFAULT 0,
    read_status TEXT NOT NULL,
    webtoon_status TEXT NOT NULL,
    date_added TEXT DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
''')

#user table
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);
''')

conn.commit()
conn.close()

print("Database initialized!")