import os
import uuid
import json
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Product, ProductImage, Order, PaymentLog 
from app.forms import CheckoutForm
from app.mpesa import send_stk_push 
from werkzeug.utils import secure_filename

# --- WHATSAPP & AI IMPORTS ---
from app.whatsapp_client import send_order_receipt, send_shipping_notification 
from app.ai_stylist import get_styling_advice, get_complete_the_look, get_chat_recommendations

main = Blueprint('main', __name__)

# --- 1. SHOPPING & PRODUCTS ---

@main.route('/')
def index():
    featured = Product.query.filter_by(is_featured=True).all()
    return render_template('index.html', featured=featured)

@main.route('/shop')
def shop():
    category = request.args.get('category', '')
    gender = request.args.get('gender', '')
    query = Product.query
    if category: query = query.filter_by(category=category)
    if gender: query = query.filter_by(gender=gender)
    products = query.order_by(Product.created_at.desc()).all()
    return render_template('shop.html', products=products)

@main.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    gallery = ProductImage.query.filter_by(product_id=product.id).all()
    
    related = Product.query.filter(
        Product.category == product.category, 
        Product.id != product.id
    ).limit(4).all()
    
    return render_template('product_detail.html', product=product, gallery=gallery, related=related)

# --- 2. CART SYSTEM ---

@main.route('/cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    size = request.form.get('size')
    quantity = int(request.form.get('quantity', 1))

    # Initialize cart if it doesn't exist
    cart = session.get('cart', {})

    # Create a unique key for product + size combo
    item_key = f"{product_id}_{size}" if size else str(product_id)

    if item_key in cart:
        cart[item_key]['quantity'] += quantity
    else:
        cart[item_key] = {
            'id': product.id,
            'name': product.name,
            'price': product.sale_price if product.sale_price else product.price,
            'image': product.image_url,
            'size': size,
            'quantity': quantity
        }

    session['cart'] = cart
    session.modified = True 
    flash(f"{product.name} added to cart!", "success")
    return redirect(url_for('main.shop'))

@main.route('/cart')
def view_cart():
    cart = session.get('cart', {})
    subtotal = sum(item['price'] * item['quantity'] for item in cart.values())
    return render_template('cart.html', cart=cart, total=subtotal)

@main.route('/cart/remove/<item_key>')
def remove_from_cart(item_key):
    cart = session.get('cart', {})
    if item_key in cart:
        cart.pop(item_key)
        session['cart'] = cart
        session.modified = True
    return redirect(url_for('main.view_cart'))

# --- 3. THE AI STYLIST & COMPLETE THE LOOK ---

@main.route('/api/ai-advice/<int:product_id>')
def ai_advice_api(product_id):
    product = Product.query.get_or_404(product_id)
    try:
        advice = get_styling_advice(product.name, product.category)
        return jsonify({"success": True, "advice": advice})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@main.route('/api/complete-look/<int:product_id>')
def complete_look_api(product_id):
    product = Product.query.get_or_404(product_id)
    try:
        # Fetch AI recommendation text/tips
        ai_data = get_complete_the_look(product.name, product.category)
        
        # Get real products from DB to display as "Recommended"
        related = Product.query.filter(Product.id != product.id).limit(3).all()
        product_list = [{
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "image": p.image_url
        } for p in related]

        return jsonify({
            "success": True, 
            "tip": ai_data.get('tip', "Perfect for a streetwear vibe."), 
            "products": product_list
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# --- 4. CHECKOUT & MPESA ---

@main.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = session.get('cart', {})
    if not cart: return redirect(url_for('main.shop'))
    
    form = CheckoutForm()
    subtotal = sum(item['price'] * item['quantity'] for item in cart.values())

    if form.validate_on_submit():
        county = form.county.data
        delivery_fee = 200 if county == 'nairobi' else 400
        total = subtotal + delivery_fee
        
        phone = form.phone.data.strip()
        if phone.startswith('0'): phone = '254' + phone[1:]
        
        order_num = f"VW-{uuid.uuid4().hex[:6].upper()}"
        new_order = Order(
            order_number=order_num,
            customer_name=form.customer_name.data,
            customer_phone=phone,
            delivery_address=form.delivery_address.data,
            items=json.dumps(cart), 
            total=total,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            payment_status='pending'
        )

        try:
            db.session.add(new_order)
            db.session.commit()
            
            response = send_stk_push(phone, total, order_num)
            if response.get('ResponseCode') == '0':
                new_order.checkout_request_id = response.get('CheckoutRequestID')
                db.session.commit()
                flash("M-Pesa prompt sent to your phone!", "success")
            
            session.pop('cart', None)
            return redirect(url_for('main.order_confirm', order_number=order_num))
        except Exception as e:
            db.session.rollback()
            flash("Error processing order. Please try again.", "danger")

    return render_template('checkout.html', form=form, total=subtotal+200)

@main.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    data = request.get_json()
    stk_callback = data['Body']['stkCallback']
    result_code = stk_callback['ResultCode']
    checkout_id = stk_callback['CheckoutRequestID']

    order = Order.query.filter_by(checkout_request_id=checkout_id).first()

    if order:
        if result_code == 0:
            order.payment_status = 'paid'
            metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
            for item in metadata:
                if item['Name'] == 'MpesaReceiptNumber':
                    order.mpesa_receipt = item['Value']
            db.session.commit()
            try:
                send_order_receipt(order)
            except:
                print("WhatsApp receipt failed to send.")
        else:
            order.payment_status = 'failed'
            db.session.commit()

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})

@main.route('/order/confirm/<order_number>')
def order_confirm(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    return render_template('order_confirm.html', order=order)