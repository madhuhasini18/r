from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import math
import os

app = Flask(__name__)
app.secret_key = 'shopwise_geo_2026'
DB = 'shopwise.db'

# ───────────────────────────────────────
# DISTANCE CALCULATION
# ───────────────────────────────────────
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

# ───────────────────────────────────────
# DATABASE
# ───────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'customer'
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS shops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        area TEXT,
        address TEXT,
        lat REAL,
        lon REAL,
        owner_id INTEGER UNIQUE
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT,
        price REAL NOT NULL,
        availability INTEGER DEFAULT 1,
        shop_id INTEGER,
        FOREIGN KEY(shop_id) REFERENCES shops(id)
    )''')

    # create default admin if not exists
    c.execute("SELECT id FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (username,password,role) VALUES ('admin','admin123','admin')"
        )

    conn.commit()
    conn.close()

# ───────────────────────────────────────
# HOME
# ───────────────────────────────────────
@app.route('/')
def home():
    if session.get('username'):
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))
        if role == 'shop_owner':
            return redirect(url_for('owner_dashboard'))
        return redirect(url_for('search_page'))

    return redirect(url_for('login'))

# ───────────────────────────────────────
# LOGIN
# ───────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
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

            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            if user['role'] == 'shop_owner':
                return redirect(url_for('owner_dashboard'))
            return redirect(url_for('search_page'))

        flash('Invalid username or password.', 'error')

    return render_template('login.html')

# ───────────────────────────────────────
# REGISTER
# ───────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        role_choice = request.form.get('role_choice', 'customer')

        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('register.html')

        try:
            conn = get_db()
            conn.execute(
                "INSERT INTO users (username,password,role) VALUES (?,?,?)",
                (username, password, role_choice)
            )
            conn.commit()

            user = conn.execute(
                "SELECT * FROM users WHERE username=?",
                (username,)
            ).fetchone()

            conn.close()

            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']

            if role_choice == 'shop_owner':
                flash('Account created! Please set up your shop.', 'success')
                return redirect(url_for('setup_shop'))

            flash('Welcome to ShopWise!', 'success')
            return redirect(url_for('search_page'))

        except sqlite3.IntegrityError:
            flash('Username already taken.', 'error')

    return render_template('register.html')

# ───────────────────────────────────────
# LOGOUT
# ───────────────────────────────────────
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ───────────────────────────────────────
# SHOP SETUP
# ───────────────────────────────────────
@app.route('/owner/setup', methods=['GET', 'POST'])
def setup_shop():
    if session.get('role') != 'shop_owner':
        return redirect(url_for('login'))

    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM shops WHERE owner_id=?",
        (session['user_id'],)
    ).fetchone()

    if existing:
        conn.close()
        return redirect(url_for('owner_dashboard'))

    if request.method == 'POST':
        name = request.form['shop_name']
        area = request.form['area']
        address = request.form['address']
        lat = request.form.get('lat', type=float)
        lon = request.form.get('lon', type=float)

        conn.execute(
            "INSERT INTO shops (name,area,address,lat,lon,owner_id) VALUES (?,?,?,?,?,?)",
            (name, area, address, lat, lon, session['user_id'])
        )
        conn.commit()
        conn.close()

        flash('Shop created successfully!', 'success')
        return redirect(url_for('owner_dashboard'))

    conn.close()
    return render_template('setup_shop.html')

# ───────────────────────────────────────
# OWNER DASHBOARD
# ───────────────────────────────────────
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

# ───────────────────────────────────────
# SEARCH PAGE
# ───────────────────────────────────────
@app.route('/search')
def search_page():
    if not session.get('username'):
        return redirect(url_for('login'))

    conn = get_db()
    categories = conn.execute(
        "SELECT DISTINCT category FROM products"
    ).fetchall()
    conn.close()

    return render_template('search.html', categories=categories)

# ───────────────────────────────────────
# ADMIN DASHBOARD
# ───────────────────────────────────────
@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = get_db()
    users = conn.execute("SELECT * FROM users").fetchall()
    shops = conn.execute("SELECT * FROM shops").fetchall()
    conn.close()

    return render_template(
        'admin_dashboard.html',
        users=users,
        shops=shops
    )

# ───────────────────────────────────────
# START APP
# ───────────────────────────────────────
if __name__ == '__main__':
    # Reset database on every deploy (for testing)
    if os.path.exists(DB):
        os.remove(DB)

    init_db()

    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
