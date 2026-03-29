from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import math
import os

app = Flask(__name__)
app.secret_key = 'shopwise_geo_2026'
DB = 'shopwise.db'

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS shops(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        area TEXT,
        address TEXT,
        lat REAL,
        lon REAL,
        owner_id INTEGER UNIQUE
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        category TEXT,
        price REAL,
        availability INTEGER,
        shop_id INTEGER
    )
    """)

    conn.commit()
    conn.close()

# create tables when app starts
init_db()

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (request.form['username'], request.form['password'])
        ).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('search_page'))

        flash("Invalid username or password")

    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        try:
            conn = get_db()
            conn.execute(
                "INSERT INTO users(username,password,role) VALUES(?,?,?)",
                (request.form['username'], request.form['password'], 'customer')
            )
            conn.commit()
            conn.close()
            flash("Registration successful")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already taken")

    return render_template('register.html')

@app.route('/search')
def search_page():
    if not session.get('username'):
        return redirect(url_for('login'))
    return render_template('search.html')
