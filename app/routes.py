import uuid
import json
from datetime import datetime
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from app import db
from app.models import Product, Order, PaymentLog # Added PaymentLog for logging
from app.forms import CheckoutForm
from app.mpesa import send_stk_push 

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

    session['cart']  = cart
    session.modified = True
    return redirect(url_for('main.cart'))

@main.route('/cart')
def cart():
    cart       = session.get('cart', {})
    cart_items = []
    subtotal   = 0

    for product_id, item in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            item_total = product.price * item['quantity']
            subtotal   += item_total
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

@main.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = session.get('cart', {})
    if not cart:
        return redirect(url_for('main.shop'))

    form = CheckoutForm()
    subtotal = sum(item['price'] * item['quantity'] for item in cart.values())

    if form.validate_on_submit():
        county = form.county.data
        delivery_fee = 200 if county == 'nairobi' else 400
        total = subtotal + delivery_fee

        phone = form.phone.data.strip()
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif phone.startswith('+'):
            phone = phone[1:]

        order_num = f"VW-{uuid.uuid4().hex[:6].upper()}"

        new_order = Order(
            order_number=order_num,
            customer_name=form.customer_name.data,
            customer_phone=phone,
            delivery_address=form.delivery_address.data,
            county=county,
            items=json.dumps(cart), 
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total=total,
            payment_status='pending'
        )

        try:
            db.session.add(new_order)
            db.session.commit()
            
            # TRIGGER M-PESA STK PUSH (Using 1 for testing as requested)
            response = send_stk_push(phone, 1, order_num)
            
            if response.get('ResponseCode') == '0':
                new_order.checkout_request_id = response.get('CheckoutRequestID')
                db.session.commit()
                flash("M-Pesa prompt sent! Enter your PIN.", "success")
            else:
                flash("Could not trigger M-Pesa prompt. Please try again.", "warning")
            
            session.pop('cart', None)
            return redirect(url_for('main.order_confirm', order_number=order_num))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error saving order: {e}")
            flash("Something went wrong. Please try again.", "danger")

    delivery_fee = 200
    total = subtotal + delivery_fee

    return render_template('checkout.html',
        form=form,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        total=total
    )

@main.route('/order/confirm/<order_number>')
def order_confirm(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    return render_template('order_confirm.html', order=order)

# --- NEW: STATUS CHECKER FOR THE FRONTEND ---
@main.route('/api/get-status/<order_number>')
def get_payment_status(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    return jsonify({
        'status': order.payment_status,
        'receipt': order.mpesa_receipt or "N/A"
    })

# --- UPDATED: THE CALLBACK LISTENER WITH FULL ERROR HANDLING ---
@main.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    data = request.get_json()
    
    if not data or 'Body' not in data:
        return jsonify({"ResultCode": 1, "ResultDesc": "Invalid Data"}), 400

    stk_callback = data['Body']['stkCallback']
    result_code = stk_callback['ResultCode']
    result_desc = stk_callback['ResultDesc']
    checkout_id = stk_callback['CheckoutRequestID']

    order = Order.query.filter_by(checkout_request_id=checkout_id).first()

    if order:
        # LOG THE ATTEMPT
        log = PaymentLog(order_id=order.id, result_code=result_code, result_description=result_desc)
        db.session.add(log)

        if result_code == 0:
            order.payment_status = 'paid'
            # Extract M-Pesa Receipt
            items = stk_callback.get('CallbackMetadata', {}).get('Item', [])
            for item in items:
                if item['Name'] == 'MpesaReceiptNumber':
                    order.mpesa_receipt = item['Value']
        elif result_code == 1:
            order.payment_status = 'insufficient_funds'
        elif result_code == 1032:
            order.payment_status = 'cancelled'
        elif result_code == 1037:
            order.payment_status = 'timeout'
        else:
            order.payment_status = 'failed'
        
        db.session.commit()
        print(f"DEBUG: Order {order.order_number} updated to {order.payment_status}")

    return jsonify({"ResultCode": 0, "ResultDesc": "Success"})