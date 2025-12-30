from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os

app = Flask(__name__, template_folder="template")
app.secret_key = "123456789"

# ---------------- Database Init ----------------
def init_db():
    if not os.path.exists('database.db'):
        with sqlite3.connect('database.db') as conn:
            conn.execute('''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                );
            ''')
            conn.execute('''
                CREATE TABLE notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
            ''')

# ---------------- Helper ----------------
def get_user_id(username):
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        user = cur.fetchone()
    return user[0] if user else None

# ---------------- Routes ----------------
@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('home.html', username=session['user'])

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        if not username or not password:
            flash("Please fill out all fields.", "error")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        try:
            with sqlite3.connect('database.db') as conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
                conn.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already exists.", "error")
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        with sqlite3.connect('database.db') as conn:
            cur = conn.cursor()
            cur.execute("SELECT password FROM users WHERE username = ?", (username,))
            user = cur.fetchone()

        if user and check_password_hash(user[0], password):
            session['user'] = username
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password.", "error")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))

# ---------------- Notes Feature ----------------
@app.route('/add_note', methods=['POST'])
def add_note():
    if 'user' not in session:
        return redirect(url_for('login'))

    title = request.form['title'].strip()
    content = request.form['content'].strip()
    user_id = get_user_id(session['user'])

    if not title or not content:
        flash("Title and content are required.", "error")
        return redirect(url_for('home'))

    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO notes (user_id, title, content) VALUES (?, ?, ?)", (user_id, title, content))
        conn.commit()

    flash("Note added successfully!", "success")
    return redirect(url_for('my_notes'))

@app.route('/my_notes')
def my_notes():
    if 'user' not in session:
        return redirect(url_for('login'))

    user_id = get_user_id(session['user'])
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, title, content FROM notes WHERE user_id = ? ORDER BY id DESC", (user_id,))
        notes = cur.fetchall()

    return render_template('my_notes.html', notes=notes)

@app.route('/edit_note/<int:note_id>', methods=['GET', 'POST'])
def edit_note(note_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    user_id = get_user_id(session['user'])
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        if request.method == 'POST':
            title = request.form['title'].strip()
            content = request.form['content'].strip()
            cur.execute("UPDATE notes SET title = ?, content = ? WHERE id = ? AND user_id = ?", (title, content, note_id, user_id))
            conn.commit()
            flash("Note updated successfully!", "success")
            return redirect(url_for('my_notes'))
        else:
            cur.execute("SELECT title, content FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id))
            note = cur.fetchone()
            if not note:
                flash("Note not found or unauthorized.", "error")
                return redirect(url_for('my_notes'))

    return render_template('edit_note.html', note_id=note_id, title=note[0], content=note[1])

@app.route('/delete_note/<int:note_id>')
def delete_note(note_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    user_id = get_user_id(session['user'])
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id))
        conn.commit()

    flash("Note deleted.", "info")
    return redirect(url_for('my_notes'))

@app.route('/duplicate_note/<int:note_id>')
def duplicate_note(note_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    user_id = get_user_id(session['user'])
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT title, content FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id))
        note = cur.fetchone()
        if note:
            cur.execute("INSERT INTO notes (user_id, title, content) VALUES (?, ?, ?)", (user_id, note[0] + " (Copy)", note[1]))
            conn.commit()
            flash("Note duplicated.", "success")
    return redirect(url_for('my_notes'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
