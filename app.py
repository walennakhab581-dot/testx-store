from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import secrets

app = Flask(__name__, template_folder='.')
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))
# ใช้ path ที่เขียนได้บน Railway
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'testx.db')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{db_path}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==================== MODELS ====================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='USER')  # USER or ADMIN
    credit = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50), default='อื่นๆ')
    description = db.Column(db.Text, default='')
    sold = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product_name = db.Column(db.String(120))
    price = db.Column(db.Float)
    license_key = db.Column(db.String(50))
    status = db.Column(db.String(30), default='สำเร็จ')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='orders')
    product = db.relationship('Product')

class Topup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(50))  # promptpay, bank, truemoney
    status = db.Column(db.String(30), default='สำเร็จ')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='topups')


# ==================== HELPERS ====================
def current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user():
            flash('กรุณาเข้าสู่ระบบก่อน', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = current_user()
        if not user or user.role != 'ADMIN':
            flash('เฉพาะแอดมินเท่านั้น', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated


# ==================== ROUTES ====================
@app.route('/')
def home():
    products = Product.query.order_by(Product.created_at.desc()).limit(6).all()
    return render_template('home.html', products=products, user=current_user())

@app.route('/products')
def products():
    q = request.args.get('q', '')
    sort = request.args.get('sort', 'newest')
    query = Product.query
    if q:
        query = query.filter(
            (Product.name.contains(q)) | (Product.category.contains(q))
        )
    if sort == 'price-asc':
        query = query.order_by(Product.price.asc())
    elif sort == 'price-desc':
        query = query.order_by(Product.price.desc())
    else:
        query = query.order_by(Product.created_at.desc())
    products = query.all()
    return render_template('products.html', products=products, user=current_user(), q=q, sort=sort)

@app.route('/buy/<int:product_id>', methods=['POST'])
@login_required
def buy(product_id):
    user = current_user()
    product = Product.query.get_or_404(product_id)

    if product.stock <= 0:
        flash('สินค้าหมดแล้ว', 'error')
        return redirect(url_for('products'))

    if user.credit < product.price:
        flash('เครดิตไม่พอ กรุณาเติมเงิน', 'error')
        return redirect(url_for('topup'))

    # หักเครดิต + ลดสต็อก
    user.credit -= product.price
    product.stock -= 1
    product.sold += 1

    # สร้างออเดอร์ + License Key
    key = 'KEY-' + secrets.token_hex(5).upper()
    order = Order(
        user_id=user.id,
        product_id=product.id,
        product_name=product.name,
        price=product.price,
        license_key=key
    )
    db.session.add(order)
    db.session.commit()

    flash(f'ซื้อสำเร็จ! License Key: {key}', 'success')
    return redirect(url_for('orders'))

@app.route('/topup', methods=['GET', 'POST'])
@login_required
def topup():
    user = current_user()
    if request.method == 'POST':
        amount = float(request.form.get('amount', 0))
        method = request.form.get('method', 'promptpay')

        if amount < 10:
            flash('จำนวนเงินขั้นต่ำ 10 บาท', 'error')
            return redirect(url_for('topup'))

        # จำลองการเติมเงินสำเร็จ
        user.credit += amount
        topup_record = Topup(user_id=user.id, amount=amount, method=method)
        db.session.add(topup_record)
        db.session.commit()

        flash(f'เติมเครดิต {amount:,.2f} บาท สำเร็จ!', 'success')
        return redirect(url_for('topup'))

    history = Topup.query.filter_by(user_id=user.id).order_by(Topup.created_at.desc()).limit(20).all()
    return render_template('topup.html', user=user, history=history)

@app.route('/orders')
@login_required
def orders():
    user = current_user()
    orders = Order.query.filter_by(user_id=user.id).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', user=user, orders=orders)

# ---------- AUTH ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user():
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('เข้าสู่ระบบสำเร็จ', 'success')
            return redirect(url_for('home'))
        flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user():
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if not username or not password:
            flash('กรุณากรอกข้อมูลให้ครบ', 'error')
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('ชื่อผู้ใช้นี้ถูกใช้แล้ว', 'error')
            return redirect(url_for('register'))
        user = User(
            username=username,
            password=generate_password_hash(password),
            role='USER',
            credit=0.0
        )
        db.session.add(user)
        db.session.commit()
        flash('สมัครสมาชิกสำเร็จ กรุณาเข้าสู่ระบบ', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('ออกจากระบบแล้ว', 'success')
    return redirect(url_for('home'))

# ---------- ADMIN ----------
@app.route('/admin')
@admin_required
def admin():
    products = Product.query.order_by(Product.created_at.desc()).all()
    orders = Order.query.order_by(Order.created_at.desc()).limit(50).all()
    users = User.query.all()
    total_sales = db.session.query(db.func.sum(Order.price)).scalar() or 0
    return render_template('admin.html',
                           user=current_user(),
                           products=products,
                           orders=orders,
                           users=users,
                           total_sales=total_sales,
                           total_products=len(products),
                           total_orders=Order.query.count(),
                           total_users=len(users))

@app.route('/admin/product/add', methods=['POST'])
@admin_required
def admin_add_product():
    name = request.form.get('name', '').strip()
    price = float(request.form.get('price', 0))
    stock = int(request.form.get('stock', 0))
    category = request.form.get('category', 'อื่นๆ').strip()
    description = request.form.get('description', '').strip()

    if not name or price <= 0:
        flash('กรุณากรอกชื่อและราคาให้ถูกต้อง', 'error')
        return redirect(url_for('admin'))

    product = Product(name=name, price=price, stock=stock, category=category, description=description)
    db.session.add(product)
    db.session.commit()
    flash('เพิ่มสินค้าสำเร็จ', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/product/edit/<int:id>', methods=['POST'])
@admin_required
def admin_edit_product(id):
    product = Product.query.get_or_404(id)
    product.name = request.form.get('name', product.name).strip()
    product.price = float(request.form.get('price', product.price))
    product.stock = int(request.form.get('stock', product.stock))
    product.category = request.form.get('category', product.category).strip()
    product.description = request.form.get('description', product.description).strip()
    db.session.commit()
    flash('แก้ไขสินค้าสำเร็จ', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/product/delete/<int:id>', methods=['POST'])
@admin_required
def admin_delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash('ลบสินค้าแล้ว', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/user/credit/<int:id>', methods=['POST'])
@admin_required
def admin_add_credit(id):
    user = User.query.get_or_404(id)
    amount = float(request.form.get('amount', 0))
    if amount != 0:
        user.credit += amount
        db.session.commit()
        flash(f'ปรับเครดิตของ {user.username} สำเร็จ', 'success')
    return redirect(url_for('admin'))


# ==================== INIT DB ====================
def init_db():
    with app.app_context():
        db.create_all()
        # สร้างแอดมินเริ่มต้น
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password=generate_password_hash('admin123'),
                role='ADMIN',
                credit=999999.00
            )
            db.session.add(admin)

        # สร้าง user ทดสอบ
        if not User.query.filter_by(username='user').first():
            normal = User(
                username='user',
                password=generate_password_hash('1234'),
                role='USER',
                credit=200.00
            )
            db.session.add(normal)

        # สินค้าตัวอย่าง
        if Product.query.count() == 0:
            samples = [
                Product(name='FAH Client Premium', price=59, stock=25, category='Game', description='ไคลเอนต์เกมคุณภาพสูง รองรับหลายโหมด'),
                Product(name='Windows 11 Pro Key', price=149, stock=50, category='Windows', description='คีย์ Windows 11 Pro ของแท้ เปิดใช้งานได้ทันที'),
                Product(name='BoostFPS Ultimate', price=99, stock=30, category='Boost', description='เพิ่ม FPS เกมลื่นไหล ลดแลค'),
                Product(name='Valorant Rank Boost', price=299, stock=10, category='Game', description='บริการบูสต์แรงค์ Valorant ปลอดภัย'),
                Product(name='Discord Nitro 1 เดือน', price=129, stock=40, category='Social', description='Nitro รายเดือน ส่งทันที'),
                Product(name='Setting PC Gaming', price=79, stock=100, category='Boost', description='ตั้งค่าคอมพิวเตอร์สำหรับเล่นเกม'),
            ]
            db.session.add_all(samples)
        db.session.commit()
        print('✅ Database initialized')


# สร้างตารางเมื่อเริ่มต้น (ทั้ง local และ Railway)
with app.app_context():
    init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
