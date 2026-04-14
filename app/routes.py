import json
import uuid
import os
import urllib.parse
import google.generativeai as genai
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required
from app import db
from app.models import Product, ProductImage, User, Order

main = Blueprint('main', __name__)

# THE CORRECT SUPABASE BASE URL
SUPABASE_URL = "https://lsjrtakduvhhbgyfalzo.supabase.co/storage/v1/object/public/product_images/"

# ── HELPER FUNCTION ──────────────────────────────────────────────────────────
def get_supabase_image(product):
    """Ensures image URLs are correctly formatted with Supabase and fixes double extensions."""
    if not product.image_url:
        return None
    
    img_path = product.image_url
    if not img_path.startswith('http'):
        if "Heart Zip" in product.name: 
            img_path = "heart-zip-pullover.jpg.jpeg"
        elif "Striped Rugby" in product.name: 
            img_path = "striped-rugby-polo.jpg.jpeg"
        elif "Black Work" in product.name: 
            img_path = "black-work-jersey.jpg.jpeg"
        
        encoded_path = urllib.parse.quote(img_path)
        return f"{SUPABASE_URL}{encoded_path}"
        
    return img_path

# ── 1. MPESA CALLBACK ────────────────────────────────────────────────────────
@main.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    data = request.get_json()
    stk_callback = data.get('Body', {}).get('stkCallback', {})
    result_code = stk_callback.get('ResultCode')
    result_desc = stk_callback.get('ResultDesc')
    checkout_id = stk_callback.get('CheckoutRequestID')

    order = Order.query.filter_by(checkout_request_id=checkout_id).first()

    if order:
        if result_code == 0:
            order.payment_status = 'Paid'
            order.order_status = 'Processing'
        elif result_code == 1032:
            order.payment_status = 'Cancelled'
        elif result_code == 2001:
            order.payment_status = 'Wrong PIN'
        elif result_code == 1:
            order.payment_status = 'Insufficient Funds'
        else:
            order.payment_status = f"Failed: {result_desc}"
        
        db.session.commit()

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200


# ── 2. PRODUCT & SHOP ROUTES ──────────────────────────────────────────────────
@main.route('/')
def index():
    products = Product.query.order_by(Product.created_at.desc()).all()
    for product in products:
        product.image_url = get_supabase_image(product)
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
    for product in products:
        product.image_url = get_supabase_image(product)

    return render_template('shop.html', products=products, category=category, gender=gender)

@main.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    product.image_url = get_supabase_image(product)
    gallery = ProductImage.query.filter_by(product_id=product.id).all()
    return render_template('product_detail.html', product=product, gallery=gallery)


# ── 3. CART MANAGEMENT ────────────────────────────────────────────────────────
@main.route('/cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    cart = session.get('cart', {})
    session.permanent = True

    size = request.form.get('size', '')
    cart_key = f"{product_id}_{size}" if size else str(product_id)
    
    image = get_supabase_image(product)

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
            product = Product.query.get(item.get('product_id'))
            current_image = get_supabase_image(product) if product else item.get('image')

            item_price    = float(item.get('price', 0))
            item_quantity = int(item.get('quantity', 1))
            item_total    = item_price * item_quantity
            subtotal     += item_total
            
            cart_items.append({
                'cart_key':    cart_key,
                'product_id': item.get('product_id'),
                'name':       item.get('name', 'Unknown'),
                'price':      item_price,
                'quantity':   item_quantity,
                'size':       item.get('size', ''),
                'image':      current_image,
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


# ── 4. DELIVERY FEES ─────────────────────────────────────────────────────────
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

KENYAN_COUNTIES = sorted(list(DELIVERY_FEES.keys()))


# ── 5. CHECKOUT ───────────────────────────────────────────────────────────────
@main.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = session.get('cart', {})
    if not cart:
        flash("Your cart is empty.", "info")
        return redirect(url_for('main.shop'))

    cart_items = []
    subtotal = 0
    for key, item in cart.items():
        item_price = float(item.get('price', 0))
        item_qty = int(item.get('quantity', 1))
        item_total = item_price * item_qty
        subtotal += item_total
        
        display_item = item.copy()
        display_item['total'] = item_total
        cart_items.append(display_item)

    if request.method == 'POST':
        customer_name    = request.form.get('customer_name', '').strip()
        customer_phone   = request.form.get('customer_phone', '').strip()
        delivery_address = request.form.get('delivery_address', '').strip()
        county           = request.form.get('county', '').strip()

        if not all([customer_name, customer_phone, delivery_address, county]):
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for('main.checkout'))

        delivery_fee = DELIVERY_FEES.get(county, 400)
        total_amount = subtotal + delivery_fee
        order_number = 'VW-' + uuid.uuid4().hex[:6].upper()

        # Clean phone number — ensure it starts with 254
        clean_phone = customer_phone.replace('+', '').replace(' ', '').replace('-', '')
        if clean_phone.startswith('0'):
            clean_phone = '254' + clean_phone[1:]
        elif not clean_phone.startswith('254'):
            clean_phone = '254' + clean_phone

        order = Order(
            order_number     = order_number,
            customer_name    = customer_name,
            customer_phone   = clean_phone,
            delivery_address = delivery_address,
            county           = county,
            items            = json.dumps(cart_items),
            subtotal         = int(subtotal),
            delivery_fee     = delivery_fee,
            total            = int(total_amount),
            payment_status   = 'Pending',
            order_status     = 'pending',
        )
        db.session.add(order)
        db.session.commit()

        session.pop('cart', None)
        return redirect(url_for('main.order_confirm', order_id=order.id))

    return render_template('checkout.html', cart_items=cart_items, subtotal=subtotal, 
                            counties=KENYAN_COUNTIES, delivery_fees=DELIVERY_FEES)


# ── 6. ORDER CONFIRMATION PAGE ────────────────────────────────────────────────
@main.route('/order/<int:order_id>')
def order_confirm(order_id):
    order = Order.query.get_or_404(order_id)
    items = json.loads(order.items)
    return render_template('order_confirm.html', order=order, items=items)


# ── 7. I HAVE PAID ────────────────────────────────────────────────────────────
@main.route('/order/<int:order_id>/paid', methods=['POST'])
def i_have_paid(order_id):
    order = Order.query.get_or_404(order_id)

    # Update status to show customer claims to have paid
    order.payment_status = 'Claimed Paid'
    db.session.commit()

    # Send instant WhatsApp acknowledgement to customer
    try:
        from app.whatsapp_client import send_whatsapp_message

        items_list = order.get_whatsapp_items()

        customer_msg = (
            f"🛍️ *VOGUE'S WEAR — ORDER RECEIVED*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Hi *{order.customer_name}*! 👋\n\n"
            f"We've received your order and are verifying your M-Pesa payment.\n\n"
            f"📌 *Order:* #{order.order_number}\n"
            f"📦 *Items:*\n{items_list}\n"
            f"💰 *Total:* KES {order.total:,}\n"
            f"📍 *Deliver to:* {order.delivery_address}, {order.county}\n\n"
            f"⏳ We'll confirm your payment shortly and notify you once your order is being prepared.\n\n"
            f"Thank you for shopping with Vogue's Wear! 🔥\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        send_whatsapp_message(order.customer_phone, customer_msg)

        # Also notify admin (your number)
        admin_msg = (
            f"🔔 *NEW ORDER — PAYMENT CLAIMED*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 Order: *#{order.order_number}*\n"
            f"👤 Customer: {order.customer_name}\n"
            f"📱 Phone: +{order.customer_phone}\n"
            f"💰 Amount: KES {order.total:,}\n"
            f"📦 Items:\n{items_list}\n"
            f"📍 Delivery: {order.delivery_address}, {order.county}\n\n"
            f"✅ Check your M-Pesa SMS for Till 3425670\n"
            f"Then go to Admin Dashboard to confirm & update order status."
        )
        send_whatsapp_message('254794724796', admin_msg)

    except Exception as e:
        print(f"WhatsApp error: {e}")

    flash("Thank you! We've received your order and are verifying your payment. Check your WhatsApp for confirmation.", "success")
    return redirect(url_for('main.order_confirm', order_id=order.id))


# ── 8. AUTH ───────────────────────────────────────────────────────────────────
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


# ── 9. AI STYLIST (Groq) ─────────────────────────────────────────────────────
@main.route('/ai-stylist/<int:product_id>', methods=['GET'])
def ai_stylist(product_id):
    try:
        from app.ai_stylist import get_complete_the_look, get_styling_advice

        product = Product.query.get_or_404(product_id)
        inventory = Product.query.filter(Product.id != product_id).all()
        result = get_complete_the_look(product, inventory)

        styling_tip = result.get('tip', 'Style it your way!')
        recommended_ids = result.get('recommended_ids', [])

        recommendations = []
        for pid in recommended_ids:
            p = Product.query.get(pid)
            if p:
                recommendations.append({
                    'id':        p.id,
                    'name':      p.name,
                    'price':     float(p.price),
                    'image_url': get_supabase_image(p),
                })

        return jsonify({
            'styling_tip':     styling_tip,
            'recommendations': recommendations,
        })

    except Exception as e:
        print(f"AI Stylist error: {e}")
        return jsonify({
            'styling_tip':     'Every outfit tells a story — make yours unforgettable.',
            'recommendations': [],
        }), 200


# ── 10. OLD API ROUTE (kept for backwards compatibility) ──────────────────────
@main.route('/api/ai-stylist', methods=['POST'])
def ai_stylist_legacy():
    try:
        data = request.get_json()
        product_name = data.get('product_name', 'item')
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            return jsonify({"suggestion": "Stylist is taking a break!"}), 200

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        prompt = f"Professional fashion stylist for Vogue's Wear. Give a 2-sentence trendy tip for: {product_name}."
        response = model.generate_content(prompt)
        return jsonify({"suggestion": response.text})
    except Exception as e:
        return jsonify({"suggestion": "I'm having trouble seeing the vision right now!"}), 200


# ── 11. SETUP ROUTES (TEMPORARY - DELETE AFTER USE) ──────────────────────────
@main.route('/setup-images')
def setup_images():
    fixes = {
        'Adidas Campus 00s (Black/White)':    'Adidas Campus 00s - BlackWhite.jfif',
        'Adidas Campus 00s (Grey/White)':     'Adidas Campus 00s - GreyWhite.jfif',
        'Adidas Samba OG (Black/White)':      'Adidas Samba OG - BlackWhite.jfif',
        'Air Jordan 4 Retro - Metallic Gold': 'Air Jordan 4 Retro - Metallic Gold.jfif',
        'Air Jordan 4 Retro (Metallic Red)':  'Air Jordan 4 Retro.jfif',
        'Nike Air Force 1 Low (Triple White)':'Nike Air Force 1.jfif',
        'Striped Rugby Polo':                 'striped-rugby-polo.jpg.jpeg',
        'Black Work Jersey':                  'black-work-jersey.jpg.jpeg',
        'Nike Dunk Olive':                    'nike-dunk-olive.jpg.jpeg',
        'LV Trainer Pink':                    'lv-trainer-pink.jpg.jpeg',
        'Heart Zip Pullover':                 'heart-zip-pullover.jpg.jpeg',
    }
    results = []
    for name, filename in fixes.items():
        p = Product.query.filter_by(name=name).first()
        if p:
            p.image_url = filename
            results.append(f'✅ Fixed: {name}')
        else:
            results.append(f'❌ Not found: {name}')
    db.session.commit()
    return '<br>'.join(results) + '<br><br>✅ Done! <a href="/">Go Home</a>'


@main.route('/setup-admin')
def setup_admin():
    existing = User.query.filter_by(username='alex').first()
    if existing:
        return 'Admin already exists!'
    user = User(username='alex', password_hash='VoguesWear2026!', is_admin=True)
    db.session.add(user)
    db.session.commit()
    return '✅ Admin created! Now delete this route!'