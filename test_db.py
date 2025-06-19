import sqlite3
conn = sqlite3.connect('app.db')
c = conn.cursor()
c.execute("SELECT * FROM exercises")
print(c.fetchall())