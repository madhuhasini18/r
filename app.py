from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3, math

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
    conn = get_db(); c = conn.cursor()
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
    c.execute("SELECT id FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username,password,role) VALUES ('admin','admin123','admin')")
    conn.commit(); conn.close()

@app.route('/')
def home():
    if session.get('username'):
        role = session.get('role')
        if role == 'admin':      return redirect(url_for('admin_dashboard'))
        if role == 'shop_owner': return redirect(url_for('owner_dashboard'))
        return redirect(url_for('search_page'))
    return render_template('index.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=?",
                            (request.form['username'], request.form['password'])).fetchone()
        conn.close()
        if user:
            session.update({'user_id': user['id'], 'username': user['username'], 'role': user['role']})
            if user['role'] == 'admin':      return redirect(url_for('admin_dashboard'))
            if user['role'] == 'shop_owner': return redirect(url_for('owner_dashboard'))
            return redirect(url_for('search_page'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username    = request.form['username'].strip()
        password    = request.form['password'].strip()
        role_choice = request.form.get('role_choice', 'customer')
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('register.html')
        try:
            conn = get_db()
            conn.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)",
                         (username, password, role_choice))
            conn.commit()
            user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            conn.close()
            session.update({'user_id': user['id'], 'username': user['username'], 'role': user['role']})
            if role_choice == 'shop_owner':
                flash('Account created! Now set up your shop details.', 'success')
                return redirect(url_for('setup_shop'))
            else:
                flash('Welcome to ShopWise!', 'success')
                return redirect(url_for('search_page'))
        except Exception:
            flash('Username already taken.', 'error')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ── SHOP SETUP (first time) ────────────────────────────────
@app.route('/owner/setup', methods=['GET','POST'])
def setup_shop():
    if session.get('role') != 'shop_owner':
        return redirect(url_for('login'))
    conn = get_db()
    existing = conn.execute("SELECT id FROM shops WHERE owner_id=?", (session['user_id'],)).fetchone()
    conn.close()
    if existing:
        return redirect(url_for('owner_dashboard'))
    if request.method == 'POST':
        name    = request.form['shop_name'].strip()
        area    = request.form['area'].strip()
        address = request.form['address'].strip()
        lat     = request.form.get('lat', type=float)
        lon     = request.form.get('lon', type=float)
        if not name or not address or lat is None or lon is None:
            flash('Please fill all fields and set your shop location.', 'error')
            return render_template('setup_shop.html')
        conn = get_db()
        conn.execute("INSERT INTO shops (name,area,address,lat,lon,owner_id) VALUES (?,?,?,?,?,?)",
                     (name, area, address, lat, lon, session['user_id']))
        conn.commit(); conn.close()
        flash(f'Shop "{name}" is live! Start adding products.', 'success')
        return redirect(url_for('owner_dashboard'))
    return render_template('setup_shop.html')

# ── OWNER DASHBOARD ────────────────────────────────────────
@app.route('/owner')
def owner_dashboard():
    if session.get('role') != 'shop_owner':
        return redirect(url_for('login'))
    conn  = get_db()
    shop  = conn.execute("SELECT * FROM shops WHERE owner_id=?", (session['user_id'],)).fetchone()
    if not shop:
        conn.close()
        flash('Please set up your shop first.', 'info')
        return redirect(url_for('setup_shop'))
    prods = conn.execute("SELECT * FROM products WHERE shop_id=? ORDER BY category, name", (shop['id'],)).fetchall()
    conn.close()
    return render_template('owner_dashboard.html', shop=shop, products=prods)

# ── EDIT SHOP ──────────────────────────────────────────────
@app.route('/owner/edit_shop', methods=['GET','POST'])
def edit_shop():
    if session.get('role') != 'shop_owner':
        return redirect(url_for('login'))
    conn = get_db()
    shop = conn.execute("SELECT * FROM shops WHERE owner_id=?", (session['user_id'],)).fetchone()
    if not shop:
        conn.close()
        return redirect(url_for('setup_shop'))
    if request.method == 'POST':
        name    = request.form['shop_name'].strip()
        area    = request.form['area'].strip()
        address = request.form['address'].strip()
        lat     = request.form.get('lat', type=float)
        lon     = request.form.get('lon', type=float)
        if not name or lat is None or lon is None:
            flash('Please fill all required fields.', 'error')
            return render_template('edit_shop.html', shop=shop)
        conn.execute("UPDATE shops SET name=?,area=?,address=?,lat=?,lon=? WHERE owner_id=?",
                     (name, area, address, lat, lon, session['user_id']))
        conn.commit(); conn.close()
        flash('Shop details updated!', 'success')
        return redirect(url_for('owner_dashboard'))
    conn.close()
    return render_template('edit_shop.html', shop=shop)

# ── PRODUCTS ───────────────────────────────────────────────
@app.route('/owner/add', methods=['GET','POST'])
def add_product():
    if session.get('role') != 'shop_owner':
        return redirect(url_for('login'))
    conn = get_db()
    shop = conn.execute("SELECT * FROM shops WHERE owner_id=?", (session['user_id'],)).fetchone()
    if not shop:
        conn.close()
        return redirect(url_for('setup_shop'))
    if request.method == 'POST':
        conn.execute("INSERT INTO products (name,category,price,availability,shop_id) VALUES (?,?,?,?,?)",
                     (request.form['name'], request.form['category'],
                      float(request.form['price']), int(request.form.get('availability', 1)), shop['id']))
        conn.commit(); conn.close()
        flash('Product added!', 'success')
        return redirect(url_for('owner_dashboard'))
    conn.close()
    return render_template('add_product.html')

@app.route('/owner/edit/<int:pid>', methods=['GET','POST'])
def edit_product(pid):
    if session.get('role') != 'shop_owner':
        return redirect(url_for('login'))
    conn = get_db()
    shop = conn.execute("SELECT * FROM shops WHERE owner_id=?", (session['user_id'],)).fetchone()
    prod = conn.execute("SELECT * FROM products WHERE id=? AND shop_id=?", (pid, shop['id'])).fetchone()
    if not prod:
        conn.close()
        flash('Product not found.', 'error')
        return redirect(url_for('owner_dashboard'))
    if request.method == 'POST':
        conn.execute("UPDATE products SET name=?,category=?,price=?,availability=? WHERE id=?",
                     (request.form['name'], request.form['category'],
                      float(request.form['price']), int(request.form.get('availability', 1)), pid))
        conn.commit(); conn.close()
        flash('Product updated!', 'success')
        return redirect(url_for('owner_dashboard'))
    conn.close()
    return render_template('edit_product.html', product=prod)

@app.route('/owner/delete/<int:pid>')
def delete_product(pid):
    if session.get('role') != 'shop_owner':
        return redirect(url_for('login'))
    conn = get_db()
    shop = conn.execute("SELECT * FROM shops WHERE owner_id=?", (session['user_id'],)).fetchone()
    conn.execute("DELETE FROM products WHERE id=? AND shop_id=?", (pid, shop['id']))
    conn.commit(); conn.close()
    flash('Product deleted.', 'info')
    return redirect(url_for('owner_dashboard'))

# ── CUSTOMER SEARCH ────────────────────────────────────────
@app.route('/search')
def search_page():
    if not session.get('username'):
        return redirect(url_for('login'))
    if session.get('role') not in ('customer', 'admin'):
        return redirect(url_for('login'))
    conn = get_db()
    categories = conn.execute("SELECT DISTINCT category FROM products ORDER BY category").fetchall()
    conn.close()
    return render_template('search.html', categories=categories)

@app.route('/results')
def results():
    if not session.get('username'):
        return redirect(url_for('login'))
    query    = request.args.get('q', '').strip()
    category = request.args.get('category', '')
    user_lat = request.args.get('lat', type=float)
    user_lon = request.args.get('lon', type=float)
    radius   = request.args.get('radius', 5.0, type=float)

    conn  = get_db()
    shops = conn.execute("SELECT * FROM shops").fetchall()
    nearby_shop_ids = []
    shop_distances  = {}
    for s in shops:
        if s['lat'] and s['lon']:
            dist = haversine(user_lat, user_lon, s['lat'], s['lon'])
            if dist <= radius:
                nearby_shop_ids.append(s['id'])
                shop_distances[s['id']] = round(dist, 2)

    results_data = []
    if nearby_shop_ids:
        placeholders = ','.join('?' * len(nearby_shop_ids))
        sql = f'''SELECT p.*, s.name as shop_name, s.area, s.address, s.lat, s.lon
                  FROM products p JOIN shops s ON p.shop_id = s.id
                  WHERE p.shop_id IN ({placeholders})'''
        params = list(nearby_shop_ids)
        if query:
            sql += ' AND LOWER(p.name) LIKE ?'
            params.append(f'%{query.lower()}%')
        if category:
            sql += ' AND p.category=?'
            params.append(category)
        sql += ' ORDER BY p.name, p.price'
        rows = conn.execute(sql, params).fetchall()
        for r in rows:
            d = dict(r)
            d['distance'] = shop_distances.get(r['shop_id'], 0)
            results_data.append(d)
    conn.close()

    grouped = {}
    for r in results_data:
        grouped.setdefault(r['name'], []).append(r)

    return render_template('results.html',
        grouped=grouped, query=query, category=category,
        user_lat=user_lat, user_lon=user_lon, radius=radius,
        total_nearby=len(nearby_shop_ids))

# ── ADMIN ──────────────────────────────────────────────────
@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    conn  = get_db()
    users = conn.execute("SELECT * FROM users ORDER BY role").fetchall()
    shops = conn.execute("SELECT s.*, u.username FROM shops s LEFT JOIN users u ON s.owner_id=u.id").fetchall()
    total = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    conn.close()
    return render_template('admin_dashboard.html', users=users, shops=shops, total_products=total)

@app.route('/admin/delete_user/<int:uid>')
def delete_user(uid):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id=?", (uid,))
    conn.commit(); conn.close()
    flash('User removed.', 'info')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
