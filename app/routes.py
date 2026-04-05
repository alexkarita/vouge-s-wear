import json
import uuid
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from app import db
from app.models import Product, ProductImage, User, Order

main = Blueprint('main', __name__)


@main.route('/')
def index():
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('index.html', products=products)


@main.route('/shop')
def shop():
    category  = request.args.get('category', '')
    gender    = request.args.get('gender', '')
    min_price = request.args.get('min_price', type=int)
    max_price = request.args.get('max_price', type=int)

    query = Product.query

    if category and category != 'All':
        query = query.filter_by(category=category)
    if gender and gender != 'All':
        query = query.filter_by(gender=gender)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    products = query.order_by(Product.created_at.desc()).all()
    return render_template('shop.html', products=products, category=category, gender=gender)


@main.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    gallery = ProductImage.query.filter_by(product_id=product.id).all()
    return render_template('product_detail.html', product=product, gallery=gallery)


@main.route('/cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    cart = session.get('cart', {})
    session.permanent = True

    size = request.form.get('size', '')
    cart_key = f"{product_id}_{size}" if size else str(product_id)
    image = product.image_url or ''

    if cart_key in cart:
        cart[cart_key]['quantity'] += 1
    else:
        cart[cart_key] = {
            'product_id': product_id,
            'name':       product.name,
            'price':      float(product.price),
            'quantity':   1,
            'size':       size,
            'image':      image,
        }

    session['cart'] = cart
    session.modified = True
    flash(f"{product.name} added to cart!", "success")
    return redirect(request.referrer or url_for('main.shop'))


@main.route('/cart')
def cart():
    session.permanent = True
    cart = session.get('cart', {})
    cart_items = []
    subtotal = 0

    for cart_key, item in cart.items():
        try:
            item_price    = float(item.get('price', 0))
            item_quantity = int(item.get('quantity', 1))
            item_total    = item_price * item_quantity
            subtotal     += item_total
            cart_items.append({
                'cart_key':   cart_key,
                'product_id': item.get('product_id', cart_key.split('_')[0]),
                'name':       item.get('name', 'Unknown'),
                'price':      item_price,
                'quantity':   item_quantity,
                'size':       item.get('size', ''),
                'image':      item.get('image', ''),
                'total':      item_total,
            })
        except Exception:
            continue

    return render_template('cart.html', cart_items=cart_items, subtotal=subtotal)


@main.route('/cart/clear')
def clear_cart():
    session.pop('cart', None)
    session.modified = True
    flash("Cart cleared.", "info")
    return redirect(url_for('main.shop'))


@main.route('/cart/remove/<path:cart_key>', methods=['POST'])
def remove_from_cart(cart_key):
    cart = session.get('cart', {})
    cart.pop(cart_key, None)
    session['cart'] = cart
    session.modified = True
    flash("Item removed from cart.", "info")
    return redirect(url_for('main.cart'))


@main.route('/cart/update/<path:cart_key>', methods=['POST'])
def update_cart(cart_key):
    cart = session.get('cart', {})
    quantity = request.form.get('quantity', type=int)
    if quantity and quantity > 0 and cart_key in cart:
        cart[cart_key]['quantity'] = quantity
    elif quantity == 0:
        cart.pop(cart_key, None)
    session['cart'] = cart
    session.modified = True
    return redirect(url_for('main.cart'))


# ── DELIVERY FEES ─────────────────────────────────────────────────────────────
DELIVERY_FEES = {
    'Nairobi': 200, 'Mombasa': 400, 'Kisumu': 400, 'Nakuru': 400,
    'Eldoret': 400, 'Thika': 300, 'Machakos': 400, 'Nyeri': 400,
    'Meru': 400, 'Kisii': 400, 'Kericho': 400, 'Embu': 400,
    'Garissa': 500, 'Kakamega': 400, 'Malindi': 400, 'Lamu': 500,
    'Baringo': 400, 'Bomet': 400, 'Bungoma': 400, 'Busia': 400,
    'Elgeyo Marakwet': 400, 'Homa Bay': 400, 'Isiolo': 400,
    'Kajiado': 300, 'Kilifi': 400, 'Kirinyaga': 300, 'Kitui': 400,
    'Kwale': 400, 'Laikipia': 400, 'Makueni': 400, 'Mandera': 500,
    'Marsabit': 500, 'Migori': 400, "Murang'a": 300, 'Nandi': 400,
    'Narok': 400, 'Nyandarua': 400, 'Nyamira': 400, 'Samburu': 500,
    'Siaya': 400, 'Taita Taveta': 400, 'Tana River': 500,
    'Tharaka Nithi': 400, 'Trans Nzoia': 400, 'Turkana': 500,
    'Uasin Gishu': 400, 'Vihiga': 400, 'Wajir': 500,
    'West Pokot': 400, 'Other': 400,
}

KENYAN_COUNTIES = sorted([
    'Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Eldoret', 'Thika',
    'Machakos', 'Nyeri', 'Meru', 'Kisii', 'Kericho', 'Embu',
    'Garissa', 'Kakamega', 'Malindi', 'Lamu', 'Baringo', 'Bomet',
    'Bungoma', 'Busia', 'Elgeyo Marakwet', 'Homa Bay', 'Isiolo',
    'Kajiado', 'Kilifi', 'Kirinyaga', 'Kitui', 'Kwale', 'Laikipia',
    'Makueni', 'Mandera', 'Marsabit', 'Migori', "Murang'a",
    'Nandi', 'Narok', 'Nyandarua', 'Nyamira', 'Samburu',
    'Siaya', 'Taita Taveta', 'Tana River', 'Tharaka Nithi',
    'Trans Nzoia', 'Turkana', 'Uasin Gishu', 'Vihiga',
    'Wajir', 'West Pokot', 'Other'
])


@main.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = session.get('cart', {})

    if not cart:
        flash("Your cart is empty.", "info")
        return redirect(url_for('main.shop'))

    cart_items = []
    subtotal = 0
    for cart_key, item in cart.items():
        try:
            item_price    = float(item.get('price', 0))
            item_quantity = int(item.get('quantity', 1))
            item_total    = item_price * item_quantity
            subtotal     += item_total
            cart_items.append({
                'cart_key': cart_key,
                'name':     item.get('name', 'Unknown'),
                'price':    item_price,
                'quantity': item_quantity,
                'size':     item.get('size', ''),
                'image':    item.get('image', ''),
                'total':    item_total,
            })
        except Exception:
            continue

    if request.method == 'POST':
        customer_name    = request.form.get('customer_name', '').strip()
        customer_phone   = request.form.get('customer_phone', '').strip()
        delivery_address = request.form.get('delivery_address', '').strip()
        county           = request.form.get('county', '').strip()

        if not all([customer_name, customer_phone, delivery_address, county]):
            flash("Please fill in all required fields.", "danger")
            return render_template('checkout.html',
                                   cart_items=cart_items,
                                   subtotal=subtotal,
                                   counties=KENYAN_COUNTIES,
                                   delivery_fees=DELIVERY_FEES)

        delivery_fee = DELIVERY_FEES.get(county, 400)
        total        = subtotal + delivery_fee
        order_number = 'VW-' + uuid.uuid4().hex[:6].upper()

        items_json = json.dumps([{
            'name':     item['name'],
            'price':    item['price'],
            'quantity': item['quantity'],
            'size':     item.get('size', ''),
        } for item in cart_items])

        order = Order(
            order_number     = order_number,
            customer_name    = customer_name,
            customer_phone   = customer_phone,
            delivery_address = delivery_address,
            county           = county,
            items            = items_json,
            subtotal         = int(subtotal),
            delivery_fee     = delivery_fee,
            total            = int(total),
            payment_status   = 'pending',
            order_status     = 'pending',
        )
        db.session.add(order)
        db.session.commit()

        # ── M-Pesa STK Push ──────────────────────────────────────────────────
        try:
            from app.mpesa import send_stk_push
            mpesa_response = send_stk_push(
                phone        = customer_phone,
                amount       = total,
                order_number = order_number
            )
            if mpesa_response.get('ResponseCode') == '0':
                order.checkout_request_id = mpesa_response.get('CheckoutRequestID')
                db.session.commit()
                flash(f"Order {order_number} placed! Check your phone for M-Pesa prompt.", "success")
            else:
                flash(f"Order placed but M-Pesa failed. Pay manually.", "danger")
        except Exception as e:
            print(f"M-Pesa error: {e}")
            flash("Order placed but M-Pesa push failed.", "danger")

        session.pop('cart', None)
        session.modified = True
        return redirect(url_for('main.order_confirm', order_id=order.id))

    return render_template('checkout.html',
                           cart_items=cart_items,
                           subtotal=subtotal,
                           counties=KENYAN_COUNTIES,
                           delivery_fees=DELIVERY_FEES)


@main.route('/order/<int:order_id>')
def order_confirm(order_id):
    order = Order.query.get_or_404(order_id)
    items = json.loads(order.items)
    return render_template('order_confirm.html', order=order, items=items)


@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        user     = User.query.filter_by(username=username).first()

        if user and user.password_hash == password:
            login_user(user)
            return redirect(url_for('admin.dashboard'))

        flash("Invalid username or password.", "danger")
    return render_template('login.html')


@main.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))


# ── ONE-TIME ADMIN SETUP ──────────────────────────────────────────────────────
# Visit https://vouge-s-wear.onrender.com/setup-admin ONCE to create your admin
# Then DELETE this route and push again for security
@main.route('/setup-admin')
def setup_admin():
    existing = User.query.filter_by(username='alex').first()
    if existing:
        return 'Admin already exists! Login with username: alex'
    user = User(
        username      = 'alex',
        password_hash = 'VoguesWear2026!',
        is_admin      = True
    )
    db.session.add(user)
    db.session.commit()
    return '✅ Admin created! Username: alex | Password: VoguesWear2026! — Now delete this route!'