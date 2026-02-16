from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os
from functools import wraps

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your-secret-key-12345'  # For session management

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# ===== Database Models =====
class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    def to_dict(self):
        """Convert product object to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'image_url': self.image_url,
            'description': self.description
        }
    
    def __repr__(self):
        return f'<Product {self.name}>'

# ===== Sample Data =====
SAMPLE_PRODUCTS = [
    {
        'name': 'Summer T-Shirt',
        'price': 19.99,
        'image_url': 'https://via.placeholder.com/400/FF6B9D/FFFFFF?text=T-Shirt',
        'description': 'Comfortable and stylish summer wear perfect for casual outings.'
    },
    {
        'name': 'Classic Denim Jeans',
        'price': 49.99,
        'image_url': 'https://via.placeholder.com/400/FFA502/FFFFFF?text=Jeans',
        'description': 'Premium quality denim with a perfect fit for any occasion.'
    },
    {
        'name': 'Designer Sneakers',
        'price': 89.99,
        'image_url': 'https://via.placeholder.com/400/FF6B9D/FFFFFF?text=Sneakers',
        'description': 'Trendy and comfortable sneakers for everyday style.'
    },
    {
        'name': 'Casual Jacket',
        'price': 59.99,
        'image_url': 'https://via.placeholder.com/400/FFA502/FFFFFF?text=Jacket',
        'description': 'Lightweight jacket perfect for layering in any season.'
    }
]

def seed_db():
    """Insert sample products if database is empty"""
    with app.app_context():
        # Check if products table has any data
        product_count = Product.query.count()
        
        if product_count == 0:
            print("\n📦 Inserting sample products...")
            for product_data in SAMPLE_PRODUCTS:
                new_product = Product(
                    name=product_data['name'],
                    price=product_data['price'],
                    image_url=product_data['image_url'],
                    description=product_data['description']
                )
                db.session.add(new_product)
            
            db.session.commit()
            print(f"✅ Added {len(SAMPLE_PRODUCTS)} sample products!")
        else:
            print(f"✅ Database already has {product_count} products. Skipping sample data.")

# ===== Create Database Tables =====
def init_db():
    """Create database and tables"""
    with app.app_context():
        db.create_all()
        print("✅ Database created successfully!")
        print("📁 Database file: shop.db")
        # Insert sample data if empty
        seed_db()

# ===== Routes =====
@app.route('/')
def index():
    """Render home page with products from database"""
    products = Product.query.all()
    # compute cart count from session
    cart = session.get('cart', {})
    cart_count = sum(cart.values()) if isinstance(cart, dict) else 0
    return render_template('index.html', products=products, cart_count=cart_count)


# ===== Shopping Cart Routes =====
@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    """Add a product to session-based cart. Accepts JSON or form data."""
    data = None
    try:
        data = request.get_json(silent=True)
    except Exception:
        data = None

    if not data:
        data = request.form

    product_id = data.get('product_id')
    if not product_id:
        return jsonify({'error': 'product_id required'}), 400

    try:
        pid = str(int(product_id))
    except Exception:
        return jsonify({'error': 'invalid product_id'}), 400

    qty = int(data.get('quantity', 1))

    cart = session.get('cart', {})
    if not isinstance(cart, dict):
        cart = {}

    cart[pid] = cart.get(pid, 0) + qty
    session['cart'] = cart
    session.modified = True

    return jsonify({'cart_count': sum(cart.values())})


@app.route('/cart')
def cart():
    """Render cart page"""
    cart = session.get('cart', {}) or {}
    items = []
    total = 0.0
    for pid, qty in cart.items():
        prod = Product.query.get(int(pid))
        if prod:
            item_total = prod.price * qty
            total += item_total
            items.append({'product': prod, 'quantity': qty, 'item_total': item_total})

    cart_count = sum(cart.values()) if isinstance(cart, dict) else 0
    return render_template('cart.html', items=items, total=total, cart_count=cart_count)


@app.route('/cart/update', methods=['POST'])
def update_cart():
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 0))
    cart = session.get('cart', {}) or {}
    if product_id in cart:
        if quantity > 0:
            cart[product_id] = quantity
        else:
            cart.pop(product_id, None)
    session['cart'] = cart
    session.modified = True
    return redirect(url_for('cart'))


@app.route('/cart/clear', methods=['POST'])
def clear_cart():
    session.pop('cart', None)
    session.modified = True
    return redirect(url_for('cart'))


# ===== Checkout =====
@app.route('/checkout', methods=['GET'])
def checkout():
    cart = session.get('cart', {}) or {}
    items = []
    total = 0.0
    for pid, qty in cart.items():
        prod = Product.query.get(int(pid))
        if prod:
            item_total = prod.price * qty
            total += item_total
            items.append({'product': prod, 'quantity': qty, 'item_total': item_total})

    if not items:
        return redirect(url_for('cart'))

    cart_count = sum(cart.values()) if isinstance(cart, dict) else 0
    return render_template('checkout.html', items=items, total=total, cart_count=cart_count)


@app.route('/checkout/process', methods=['POST'])
def checkout_process():
    # Simple mock processing: collect form data, then clear cart and show success
    name = request.form.get('name')
    email = request.form.get('email')
    address = request.form.get('address')

    # Here you'd integrate with payment gateway. We'll just clear the cart.
    order_info = {
        'name': name,
        'email': email,
        'address': address
    }
    session.pop('cart', None)
    session.modified = True

    return render_template('checkout_success.html', order=order_info)

# ===== Login & Admin Routes =====
def login_required(f):
    """Decorator to check if user is logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Simple authentication (hardcoded)
        if username == 'admin' and password == '1234':
            session['admin_logged_in'] = True
            session['admin_username'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid username or password!')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Admin logout"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Admin dashboard"""
    products = Product.query.all()
    return render_template('admin.html', products=products)

@app.route('/add-product', methods=['GET', 'POST'])
@login_required
def add_product():
    """Add new product"""
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        image_url = request.form.get('image_url')
        description = request.form.get('description', '')
        
        try:
            new_product = Product(
                name=name,
                price=float(price),
                image_url=image_url,
                description=description
            )
            db.session.add(new_product)
            db.session.commit()
            return redirect(url_for('dashboard'))
        except Exception as e:
            return render_template('admin.html', error=f'Error adding product: {str(e)}')
    
    return render_template('admin.html')

@app.route('/delete-product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    """Delete product by ID"""
    try:
        product = Product.query.get_or_404(product_id)
        db.session.delete(product)
        db.session.commit()
    except Exception as e:
        pass
    
    return redirect(url_for('dashboard'))

@app.route('/api/products')
def get_products():
    """Get all products from database"""
    products = Product.query.all()
    return jsonify([product.to_dict() for product in products])

@app.route('/api/products/<int:product_id>')
def get_product(product_id):
    """Get single product by ID"""
    product = Product.query.get_or_404(product_id)
    return jsonify(product.to_dict())

@app.route('/admin')
@login_required
def admin_old():
    """Admin page for managing products (legacy route)"""
    return redirect(url_for('dashboard'))

# ===== Error Handlers =====
@app.errorhandler(404)
def page_not_found(error):
    return jsonify({'error': 'Page not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

# ===== Main =====
if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Run Flask app
    print("\n🚀 Starting Flask app on http://localhost:5000/")
    app.run(debug=True, host='localhost', port=5000)
