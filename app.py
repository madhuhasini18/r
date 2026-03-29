from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import math

app = Flask(__name__)
app.secret_key = 'shopwise_secret'
DB = 'shopwise.db'

# -------------------------
# Database connection
# -------------------------
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# -------------------------
# Database initialization
# -------------------------
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
# Distance calculation
# -------------------------
def haversine(lat1, lon1, lat2, lon2):
    if not lat1 or not lat2:
        return None
    R = 6371
    dlat = math.radians(float(lat2) - float(lat1))
    dlon = math.radians(float(lon2) - float(lon1))
    a = math.sin(dlat/2)**2 + math.cos(math.radians(float(lat1))) * math.cos(math.radians(float(lat2))) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# -------------------------
# Home
# -------------------------
@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('search_page'))

# -------------------------
# Register
# -------------------------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        try:
            conn = get_db()
            conn.execute(
                "INSERT INTO users(username,password,role) VALUES(?,?,?)",
                (
                    request.form['username'],
                    request.form['password'],
                    request.form['role']
                )
            )
            conn.commit()
            conn.close()
            flash("Registration successful")
            return redirect(url_for('login'))
        except:
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
# Customer search
# -------------------------
@app.route('/search')
def search_page():
    if 'username' not in session:
        return redirect(url_for('login'))

    product = request.args.get('product')
    lat = request.args.get('lat')
    lon = request.args.get('lon')

    conn = get_db()

    if product:
        results = conn.execute("""
        SELECT p.name, p.price, s.name AS shop, s.lat, s.lon
        FROM products p
        JOIN shops s ON p.shop_id = s.id
        WHERE p.name LIKE ?
        """, ('%' + product + '%',)).fetchall()

        enriched = []
        for r in results:
            dist = haversine(lat, lon, r['lat'], r['lon'])
            enriched.append({
                'name': r['name'],
                'price': r['price'],
                'shop': r['shop'],
                'distance': round(dist,2) if dist else None
            })

        enriched.sort(key=lambda x: (x['distance'] is None, x['distance']))
    else:
        enriched = []

    conn.close()
    return render_template('search.html', results=enriched)

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
# Run locally
# -------------------------
if __name__ == '__main__':
    app.run(debug=True)
