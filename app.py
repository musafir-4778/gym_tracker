# app.py (main Flask app)
from flask import Flask, render_template, request, redirect, session, url_for, Response
import sqlite3
import shutil
import csv
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = 'secret123'

MASTER_EXERCISES = [
    {'name': 'Push Up', 'muscle': 'Chest', 'icon': '🤸', 'type': 'Push'},
    {'name': 'Bench Press', 'muscle': 'Chest', 'icon': '🏋️', 'type': 'Push'},
    {'name': 'Pull Up', 'muscle': 'Back', 'icon': '🧗', 'type': 'Pull'},
    {'name': 'Deadlift', 'muscle': 'Back', 'icon': '🏋️‍♂️', 'type': 'Pull'},
    {'name': 'Squat', 'muscle': 'Legs', 'icon': '🏋️', 'type': 'Legs'},
    {'name': 'Lunges', 'muscle': 'Legs', 'icon': '🦵', 'type': 'Legs'},
    {'name': 'Bicep Curl', 'muscle': 'Arms', 'icon': '💪', 'type': 'Custom'},
    {'name': 'Tricep Dip', 'muscle': 'Arms', 'icon': '👐', 'type': 'Custom'},
]

# --- DATABASE SETUP ---
DB = 'app.db'

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT
        );

        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            muscle_group TEXT,
            icon TEXT,
            workout_type TEXT
        );

        CREATE TABLE IF NOT EXISTS workout_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            exercise_name TEXT,
            reps INTEGER,
            weight REAL,
            log_date TEXT
        );
        ''')

# --- AUTH ROUTES ---
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email=? AND password=?', (email, password)).fetchone()
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            return redirect(url_for('my_workout'))
        else:
            return 'Invalid credentials'
    return render_template('auth.html')

@app.route('/signup', methods=['POST'])
def signup():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    db = get_db()
    try:
        db.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)', (name, email, password))
        db.commit()
        return redirect(url_for('login'))
    except:
        return 'Email already exists'

# --- WORKOUT ROUTES ---
@app.route('/my-workout')
def my_workout():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_name = session.get('user_name', 'User')
    db = get_db()

    push = db.execute('SELECT * FROM exercises WHERE user_id=? AND workout_type=?', (user_id, 'Push')).fetchall()
    pull = db.execute('SELECT * FROM exercises WHERE user_id=? AND workout_type=?', (user_id, 'Pull')).fetchall()
    legs = db.execute('SELECT * FROM exercises WHERE user_id=? AND workout_type=?', (user_id, 'Legs')).fetchall()
    custom = db.execute('SELECT * FROM exercises WHERE user_id=? AND workout_type=?', (user_id, 'Custom')).fetchall()

    return render_template('my_workout.html',
                           push_exercises=push,
                           pull_exercises=pull,
                           leg_exercises=legs,
                           custom_exercises=custom,
                           today=date.today(),
                           user=user_name)

@app.route('/log-exercise', methods=['POST'])
def log_exercise():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    exercise_name = request.form['exercise_name']
    reps_list = request.form.getlist('reps[]')
    weight_list = request.form.getlist('weight[]')
    user_id = session['user_id']
    log_date = datetime.now().isoformat(timespec='seconds')

    db = get_db()
    for reps, weight in zip(reps_list, weight_list):
        db.execute('INSERT INTO workout_logs (user_id, exercise_name, reps, weight, log_date) VALUES (?, ?, ?, ?, ?)',
                   (user_id, exercise_name, reps, weight, log_date))
    db.commit()
    return redirect(url_for('my_workout'))

@app.route('/add-exercise', methods=['GET', 'POST'])
def add_exercise():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        selected = request.form.getlist('selected_exercises[]')
        user_id = session['user_id']
        db = get_db()

        for exercise_name in selected:
            for ex in MASTER_EXERCISES:
                if ex['name'] == exercise_name:
                    db.execute('''
                        INSERT INTO exercises (user_id, name, muscle_group, icon, workout_type)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (user_id, ex['name'], ex['muscle'], ex['icon'], ex['type']))
                    break
        db.commit()
        return redirect(url_for('my_workout'))

    return render_template('add_exercise.html', exercises=MASTER_EXERCISES)

@app.route('/progress', methods=['GET', 'POST'])
def select_progress_graph():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    user_id = session['user_id']

    # Get only user's added exercises
    exercises = db.execute('''
        SELECT DISTINCT name FROM exercises WHERE user_id = ?
    ''', (user_id,)).fetchall()

    if request.method == 'POST':
        selected_ex = request.form['exercise_name']
        return redirect(url_for('exercise_progress', exercise_name=selected_ex))

    return render_template('select_graph.html', exercises=exercises)

@app.route('/exercise-progress/<exercise_name>')
def exercise_progress(exercise_name):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    db = get_db()

    logs = db.execute('''
        SELECT id, reps, weight
        FROM workout_logs
        WHERE user_id = ? AND exercise_name = ?
        ORDER BY id
    ''', (user_id, exercise_name)).fetchall()

    labels = list(range(1, len(logs) + 1))
    weights = [log['weight'] for log in logs]
    reps = [log['reps'] for log in logs]
    volumes = [log['weight'] * log['reps'] for log in logs]

    return render_template('progress.html',
                           exercise_name=exercise_name,
                           labels=labels,
                           weights=weights,
                           reps=reps,
                           volumes=volumes)

@app.route('/history', methods=['GET', 'POST'])
def history():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    db = get_db()

    exercises = db.execute('''
        SELECT DISTINCT exercise_name
        FROM workout_logs
        WHERE user_id = ?
    ''', (user_id,)).fetchall()

    selected_exercise = request.form.get('exercise_name')
    selected_date = request.form.get('log_date')

    query = 'SELECT * FROM workout_logs WHERE user_id = ?'
    params = [user_id]

    if selected_exercise:
        query += ' AND exercise_name = ?'
        params.append(selected_exercise)

    if selected_date:
        query += ' AND DATE(log_date) = ?'
        params.append(selected_date)

    query += ' ORDER BY DATE(log_date) DESC, id DESC'

    logs = db.execute(query, params).fetchall()

    return render_template('history.html',
                           logs=logs,
                           exercises=exercises,
                           user=session['user_name'])

@app.route('/export-logs')
def export_logs():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    db = get_db()
    logs = db.execute('SELECT * FROM workout_logs WHERE user_id = ?', (user_id,)).fetchall()

    def generate():
        data = ['ID,Exercise Name,Reps,Weight,Date\n']
        for row in logs:
            data.append(f"{row['id']},{row['exercise_name']},{row['reps']},{row['weight']},{row['log_date']}\n")
        return data

    return Response(generate(), mimetype='text/csv',
                    headers={"Content-Disposition": "attachment; filename=workout_logs.csv"})

def backup_db():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    shutil.copyfile(DB, f'backup_{timestamp}.db')

if __name__ == '__main__':
    init_db()
    backup_db()
    app.run(debug=True)
