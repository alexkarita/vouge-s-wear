from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify
from app.models import Product

main = Blueprint('main', __name__)

@main.route('/')
def index():
    featured = Product.query.filter_by(is_featured=True).all()
    return render_template('index.html', featured=featured)

@main.route('/shop')
def shop():
    category  = request.args.get('category', '')
    gender    = request.args.get('gender', '')
    min_price = request.args.get('min_price', 0, type=int)
    max_price = request.args.get('max_price', 99999, type=int)

    query = Product.query
    if category:
        query = query.filter_by(category=category)
    if gender:
        query = query.filter_by(gender=gender)
    query = query.filter(
        Product.price >= min_price,
        Product.price <= max_price
    )
    products = query.order_by(Product.created_at.desc()).all()

    return render_template('shop.html',
        products=products,
        category=category,
        gender=gender
    )

@main.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    related = Product.query.filter(
        Product.category == product.category,
        Product.id != product.id
    ).limit(4).all()
    return render_template('product_detail.html', product=product, related=related)

@main.route('/cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    size    = request.form.get('size', '')

    cart = session.get('cart', {})
    key  = str(product_id)

    if key in cart:
        cart[key]['quantity'] += 1
    else:
        cart[key] = {
            'quantity': 1,
            'size':     size,
            'name':     product.name,
            'price':    product.price,
        }

    session['cart']     = cart
    session.modified    = True
    return redirect(url_for('main.cart'))

@main.route('/cart')
def cart():
    cart        = session.get('cart', {})
    cart_items  = []
    subtotal    = 0

    for product_id, item in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            item_total = product.price * item['quantity']
            subtotal  += item_total
            cart_items.append({
                'product':    product,
                'quantity':   item['quantity'],
                'size':       item['size'],
                'item_total': item_total,
            })

    return render_template('cart.html',
        cart_items=cart_items,
        subtotal=subtotal
    )

@main.route('/cart/remove/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    cart.pop(str(product_id), None)
    session['cart']  = cart
    session.modified = True
    return redirect(url_for('main.cart'))

@main.route('/cart/update/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    quantity = request.form.get('quantity', 1, type=int)
    cart     = session.get('cart', {})
    key      = str(product_id)

    if key in cart:
        if quantity <= 0:
            cart.pop(key, None)
        else:
            cart[key]['quantity'] = quantity

    session['cart']  = cart
    session.modified = True
    return redirect(url_for('main.cart'))