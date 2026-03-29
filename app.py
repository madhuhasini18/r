from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import math
import os

app = Flask(__name__)
app.secret_key = 'shopwise_secret'
DB = 'shopwise.db'

# -------------------------
# Database helpers
# -------------------------
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

init_db()

# -------------------------
# Home
# -------------------------
@app.route('/')
def home():
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    if session.get('role') == 'shop_owner':
        return redirect(url_for('owner_dashboard'))
    if session.get('username'):
        return redirect(url_for('search_page'))
    return redirect(url_for('login'))

# -------------------------
# Register
# -------------------------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        try:
            conn = get_db()
            conn.execute(
                "INSERT INTO users(username,password,role) VALUES(?,?,?)",
                (username, password, role)
            )
            conn.commit()
            conn.close()
            flash("Registration successful. Please login.")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already exists")

    return render_template('register.html')

# -------------------------
# Login
# -------------------------
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
            session['role'] = user['role']
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password")

    return render_template('login.html')

# -------------------------
# Logout
# -------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# -------------------------
# Customer search page
# -------------------------
@app.route('/search')
def search_page():
    if not session.get('username'):
        return redirect(url_for('login'))
    return render_template('search.html')

# -------------------------
# Seller dashboard
# -------------------------
@app.route('/owner')
def owner_dashboard():
    if session.get('role') != 'shop_owner':
        return redirect(url_for('login'))

    conn = get_db()
    shop = conn.execute(
        "SELECT * FROM shops WHERE owner_id=?",
        (session['user_id'],)
    ).fetchone()

    if not shop:
        conn.close()
        return redirect(url_for('setup_shop'))

    products = conn.execute(
        "SELECT * FROM products WHERE shop_id=?",
        (shop['id'],)
    ).fetchall()

    conn.close()
    return render_template('owner_dashboard.html', shop=shop, products=products)

# -------------------------
# Setup shop
# -------------------------
@app.route('/owner/setup', methods=['GET','POST'])
def setup_shop():
    if session.get('role') != 'shop_owner':
        return redirect(url_for('login'))

    if request.method == 'POST':
        conn = get_db()
        conn.execute("""
        INSERT INTO shops(name,area,address,lat,lon,owner_id)
        VALUES(?,?,?,?,?,?)
        """, (
            request.form['shop_name'],
            request.form['area'],
            request.form['address'],
            request.form.get('lat'),
            request.form.get('lon'),
            session['user_id']
        ))
        conn.commit()
        conn.close()
        return redirect(url_for('owner_dashboard'))

    return render_template('setup_shop.html')

# -------------------------
# Add product
# -------------------------
@app.route('/owner/add_product', methods=['POST'])
def add_product():
    if session.get('role') != 'shop_owner':
        return redirect(url_for('login'))

    conn = get_db()
    shop = conn.execute(
        "SELECT id FROM shops WHERE owner_id=?",
        (session['user_id'],)
    ).fetchone()

    conn.execute("""
    INSERT INTO products(name,category,price,availability,shop_id)
    VALUES(?,?,?,?,?)
    """, (
        request.form['name'],
        request.form['category'],
        request.form['price'],
        1,
        shop['id']
    ))
    conn.commit()
    conn.close()
    return redirect(url_for('owner_dashboard'))

# -------------------------
# Admin dashboard
# -------------------------
@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = get_db()
    users = conn.execute("SELECT * FROM users").fetchall()
    shops = conn.execute("SELECT * FROM shops").fetchall()
    conn.close()

    return render_template('admin_dashboard.html', users=users, shops=shops)

# -------------------------
# Run local
# -------------------------
if __name__ == '__main__':
    app.run(debug=True)
