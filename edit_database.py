import sqlite3
from werkzeug.security import generate_password_hash

connection = sqlite3.connect("sqlite.db", check_same_thread=False)
cursor = connection.cursor()

cursor.execute('DROP TABLE IF EXISTS user;')

cursor.execute('''
CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);
''')

username = 'prosto_lipton'
email = 'polinademi78@gmail.com'
password = 'confidentiality83'
password_hash = generate_password_hash(password)

cursor.execute(
    'INSERT INTO user (username, email, password_hash) VALUES (?, ?, ?)',
    (username, email, password_hash)
)

try:
    cursor.execute('ALTER TABLE post ADD COLUMN author_id INTEGER;')
except sqlite3.OperationalError:
    pass

cursor.execute('UPDATE post SET author_id = 1;')

connection.commit()
connection.close()