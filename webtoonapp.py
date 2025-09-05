import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # needed for session management

def titlecase(value):
    return value.title() if value else ''

app.jinja_env.filters['titlecase'] = titlecase

#database connection
def get_db_connection():
    conn = sqlite3.connect('webtoons.db')
    conn.row_factory = sqlite3.Row
    return conn

#initialize list for not logged in users
@app.before_request
def ensure_temp_webtoons():
    if 'temp_webtoons' not in session:
        session['temp_webtoons'] = []

#load logged in users before request
@app.before_request
def load_logged_in_users():
    g.user = None
    if "user_id" in session:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        conn.close()
        g.user = user

#register page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        if not username or not password:
            flash("Username and password required")
            return redirect(url_for('register'))
        
        conn = get_db_connection()
        existing_user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if existing_user:
            flash("Username already exists")
            conn.close()
            return redirect(url_for('register'))
        
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                     (username, generate_password_hash(password)))
        conn.commit()
        conn.close()
        flash("Account created! Please log in.")
        return redirect(url_for('login'))

    return render_template('register.html')

#login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session.clear()
            session['user_id'] = user['id']
            flash(f'Welcome, {username}!')
            return redirect(url_for('home'))

        else:
            flash("Invalid username or password")
            return redirect(url_for('login'))

    return render_template('login.html')

#logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

#home page
@app.route('/')
def home():
    #if logged in fetch data
    if 'user_id' in session:
        user_id = session['user_id']
        conn = get_db_connection()
        webtoons_result= conn.execute('SELECT * FROM webtoons WHERE user_id = ?', (user_id,)).fetchall()
        conn.close()

    #else use temp webtoon list
    else:
        webtoons_result = session.get('temp_webtoons', [])

    return render_template('index.html', webtoons=webtoons_result)

#add webtoon page
@app.route('/add', methods=['GET', 'POST'])
def add_webtoon():
    if request.method == 'POST':
        title = request.form['title']
        chapter = request.form['chapter']
        read_status = request.form['read_status']
        webtoon_status = request.form['webtoon_status']

        if len(title) > 80: #chracter limit of title
            return render_template("add.html", error="Title too long (max 80 characters).")

        if not title or not read_status or not webtoon_status:
            return "All fields except chapter are required.", 400

        date_added = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        #logged in, store data
        if 'user_id' in session:
            conn = get_db_connection()
            conn.execute(
                'INSERT INTO webtoons (title, chapter, read_status, webtoon_status, date_added, user_id) VALUES (?, ?, ?, ?, ?, ?)',
                (title, chapter, read_status, webtoon_status, date_added, session['user_id'])
            )
            conn.commit()
            conn.close()
        
        #not logged in, use temp storage 
        else:
            temp_list = session['temp_webtoons']
            temp_list.append({
                'id': len(temp_list)+1, #fake ID
                'title': title,
                'chapter': chapter,
                'read_status': read_status,
                'webtoon_status': webtoon_status,
                'date_added': date_added,
                'user_id': None
            })
            session['temp_webtoons'] = temp_list  #save back to session

        return redirect(url_for('home'))
    
    return render_template('add.html')

#edit webtoon page
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_webtoon(id):
    #logged in
    if 'user_id' in session:
        conn = get_db_connection()
        webtoon_data = conn.execute('SELECT * FROM webtoons WHERE id = ? and user_id = ?', (id, session['user_id'])).fetchone()

        if webtoon_data is None:
            conn.close()
            return "Webtoon not found or access denied", 404 
        
        if request.method == 'POST':
            title = request.form['title']
            chapter = request.form['chapter']
            read_status = request.form['read_status']
            webtoon_status = request.form['webtoon_status']

            if len(title) > 80: #chracter limit of title
                return render_template("edit.html", webtoon=webtoon_data, error="Title too long (max 80 characters).")

            if  not title or not read_status or not webtoon_status:
                conn.close()
                return "All fields except chapter are required.", 400

            conn.execute('''
                    UPDATE webtoons
                    SET title = ?, chapter = ?, read_status = ?, webtoon_status = ?
                    WHERE id = ?
                ''', (title, chapter, read_status, webtoon_status, id))

            conn.commit()
            conn.close()
            return redirect(url_for('home'))

        conn.close()
        return render_template('edit.html', webtoon=webtoon_data)
    
    else: #not logged in, use temp list
        temp_list = session.get('temp_webtoons', [])
        webtoon_data = next((w for w in temp_list if w['id'] == id), None)
        if webtoon_data is None:
            return "Webtoon not found", 404

        if request.method == 'POST':
            webtoon_data['title'] = request.form['title']
            webtoon_data['chapter'] = request.form['chapter']
            webtoon_data['read_status'] = request.form['read_status']
            webtoon_data['webtoon_status'] = request.form['webtoon_status']

            session['temp_webtoons'] = temp_list  # save changes

            return redirect(url_for('home'))

    return render_template('edit.html', webtoon=webtoon_data)

#delete webtoon function
@app.route('/delete/<int:id>', methods=['POST'])
def delete_webtoon(id):
    #logged in
    if 'user_id' in session:
        conn = get_db_connection()
        conn.execute('DELETE FROM webtoons WHERE id = ? and user_id = ?', (id, session['user_id']))
        conn.commit()
        conn.close()
    
    #not logged in
    else:
        temp_list = session.get('temp_webtoons', [])
        temp_list = [w for w in temp_list if w['id'] != id]
        session['temp_webtoons'] = temp_list

    return redirect(url_for('home'))

#delete all webtoon function
@app.route('/delete_all', methods=['POST'])
def delete_all():
    #logged in
    if 'user_id' in session:
        conn = get_db_connection()
        conn.execute("DELETE FROM webtoons WHERE user_id = ?", (session['user_id'],)) #delete all rows from user
        conn.execute("DELETE FROM sqlite_sequence WHERE name='webtoons'") #reset IDs
        conn.commit()
        conn.close()

    #not logged in
    else:
        session['temp_webtoons'] = []

    return redirect(url_for('home'))

#search bar
@app.route('/search', methods=['GET'])
def search():
    query = request.args.get("q", "").strip()
    query_pattern = f'%{query}%'

    #logged in
    if 'user_id' in session:
        conn = get_db_connection()
        webtoons_result = conn.execute(
            "SELECT * FROM webtoons WHERE user_id = ? AND title LIKE ? ORDER BY date_added DESC",
            (session['user_id'], query_pattern)
        ).fetchall()
        conn.close()
    
    #not logged in, use temp list
    else:
        temp_list = session.get('temp_webtoons', [])
        if query:
            webtoons_result = [w for w in temp_list if query.lower() in w['title'].lower()]
        else:
            webtoons_result = temp_list

    return render_template("index.html", webtoons=webtoons_result, search_query=query)

#run code
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)

    