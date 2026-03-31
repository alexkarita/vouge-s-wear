import os
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import func
from app import db
from app.models import Product, ProductImage, Order

admin_bp = Blueprint('admin', __name__)

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ── DASHBOARD ────────────────────────────────────────────────────────────────
@admin_bp.route('/admin/dashboard')
@login_required
def dashboard():
    if not current_user.is_admin:
        return redirect(url_for('main.index'))

    products = Product.query.order_by(Product.id.desc()).all()
    orders   = Order.query.order_by(Order.id.desc()).limit(10).all()

    stats = {
        'total':          Product.query.count(),
        'on_sale':        Product.query.filter(Product.sale_price.isnot(None)).count(),
        'low_stock':      Product.query.filter(Product.stock > 0, Product.stock < 5).count(),
        'out_of_stock':   Product.query.filter_by(stock=0).count(),
        'total_orders':   Order.query.count(),
        'pending_orders': Order.query.filter_by(order_status='pending').count(),
    }
    return render_template('admin/dashboard.html', products=products, orders=orders, stats=stats)


# ── ADD PRODUCT ───────────────────────────────────────────────────────────────
@admin_bp.route('/admin/add-product', methods=['GET', 'POST'])
@admin_bp.route('/admin/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        name        = request.form.get('name', '').strip()
        category    = request.form.get('category', '').strip()
        gender      = request.form.get('gender', '').strip()
        price       = request.form.get('price', type=int)
        sizes       = request.form.get('sizes', '').strip()
        description = request.form.get('description', '').strip()
        stock       = request.form.get('stock', 0, type=int)
        is_featured = request.form.get('is_featured') == '1'
        sale_price  = request.form.get('sale_price', type=int)

        if not all([name, category, gender, price, sizes]):
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for('admin.add_product'))

        try:
            new_product = Product(
                name=name, category=category, gender=gender,
                price=price, sale_price=sale_price if sale_price else None,
                sizes=sizes, description=description,
                stock=stock, is_featured=is_featured,
            )
            db.session.add(new_product)
            db.session.flush()

            files = request.files.getlist('photos')
            for i, file in enumerate(files[:5]):
                if file and file.filename != '' and allowed_file(file.filename):
                    filename  = secure_filename(file.filename)
                    save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    file.save(save_path)
                    db.session.add(ProductImage(url=filename, product_id=new_product.id))
                    if i == 0:
                        new_product.image_url = filename

            db.session.commit()
            flash(f"Product '{name}' added successfully!", "success")
            return redirect(url_for('admin.dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error adding product: {str(e)}", "danger")
            return redirect(url_for('admin.add_product'))

    return render_template('admin/add_product.html')


# ── EDIT PRODUCT ──────────────────────────────────────────────────────────────
@admin_bp.route('/admin/edit-product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for('main.index'))

    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        product.name        = request.form.get('name', '').strip()
        product.category    = request.form.get('category', '').strip()
        product.gender      = request.form.get('gender', '').strip()
        product.price       = request.form.get('price', type=int)
        product.sizes       = request.form.get('sizes', '').strip()
        product.description = request.form.get('description', '').strip()
        product.stock       = request.form.get('stock', 0, type=int)
        product.is_featured = request.form.get('is_featured') == '1'
        sale_price          = request.form.get('sale_price', type=int)
        product.sale_price  = sale_price if sale_price else None

        files = request.files.getlist('photos')
        for i, file in enumerate(files[:5]):
            if file and file.filename != '' and allowed_file(file.filename):
                filename  = secure_filename(file.filename)
                save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(save_path)
                db.session.add(ProductImage(url=filename, product_id=product.id))
                if not product.image_url:
                    product.image_url = filename

        db.session.commit()
        flash(f"'{product.name}' updated successfully!", "success")
        return redirect(url_for('admin.dashboard'))

    gallery = ProductImage.query.filter_by(product_id=product.id).all()
    return render_template('admin/edit_product.html', product=product, gallery=gallery)


# ── DELETE PRODUCT ────────────────────────────────────────────────────────────
@admin_bp.route('/admin/delete-product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for('main.index'))

    product       = Product.query.get_or_404(product_id)
    upload_folder = current_app.config['UPLOAD_FOLDER']

    def remove_file(filename):
        if filename:
            path = os.path.join(upload_folder, os.path.basename(filename))
            if os.path.exists(path):
                try: os.remove(path)
                except: pass

    remove_file(product.image_url)
    for img in ProductImage.query.filter_by(product_id=product.id).all():
        remove_file(img.url)

    name = product.name
    db.session.delete(product)
    db.session.commit()
    flash(f"'{name}' deleted.", "success")
    return redirect(url_for('admin.dashboard'))


# ── TOGGLE FEATURED ───────────────────────────────────────────────────────────
@admin_bp.route('/admin/toggle-featured/<int:product_id>', methods=['POST'])
@login_required
def toggle_featured(product_id):
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for('main.index'))

    product             = Product.query.get_or_404(product_id)
    product.is_featured = not product.is_featured
    db.session.commit()
    flash(f"'{product.name}' featured status updated.", "success")
    return redirect(url_for('admin.dashboard'))


# ── ORDER DETAIL ──────────────────────────────────────────────────────────────
@admin_bp.route('/admin/order/<int:order_id>')
@login_required
def order_detail(order_id):
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for('main.index'))

    order = Order.query.get_or_404(order_id)
    items = json.loads(order.items)
    return render_template('admin/order_detail.html', order=order, items=items)


# ── UPDATE ORDER STATUS + WHATSAPP NOTIFICATION ───────────────────────────────
@admin_bp.route('/admin/update-order-status/<int:order_id>', methods=['POST'])
@login_required
def update_order_status(order_id):
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for('main.index'))

    order      = Order.query.get_or_404(order_id)
    new_status = request.form.get('status', order.order_status)
    old_status = order.order_status
    order.order_status = new_status
    db.session.commit()

    # ── Send WhatsApp to customer when status changes ─────────────────────────
    if new_status != old_status:
        try:
            from app.whatsapp_client import send_whatsapp_message

            if new_status == 'packed':
                msg = (
                    f"📦 *VOGUE'S WEAR: ORDER PACKED*\n"
                    f"--------------------------------\n"
                    f"Hi *{order.customer_name}*,\n"
                    f"Your order *#{order.order_number}* has been packed and is ready for dispatch!\n\n"
                    f"📍 Delivering to: {order.delivery_address}\n"
                    f"📅 Expected: {order.get_delivery_date()}\n\n"
                    f"We'll notify you once it's on the way. ✨"
                )
            elif new_status == 'shipped':
                msg = (
                    f"🚀 *VOGUE'S WEAR: ORDER SHIPPED*\n"
                    f"--------------------------------\n"
                    f"Hi *{order.customer_name}*,\n"
                    f"Great news! Your order *#{order.order_number}* is on the move! 🎉\n\n"
                    f"📦 Status: Out for Delivery\n"
                    f"📅 Expected: {order.get_delivery_date()}\n"
                    f"📍 To: {order.delivery_address}\n\n"
                    f"Get ready to rock your new style! 🔥"
                )
            elif new_status == 'delivered':
                msg = (
                    f"✅ *VOGUE'S WEAR: ORDER DELIVERED*\n"
                    f"--------------------------------\n"
                    f"Hi *{order.customer_name}*,\n"
                    f"Your order *#{order.order_number}* has been delivered! 🎊\n\n"
                    f"We hope you love your new items.\n"
                    f"Please leave us a review — it means a lot! ⭐\n\n"
                    f"Thank you for shopping with Vogue's Wear. 🛍️"
                )
            else:
                msg = None

            if msg:
                send_whatsapp_message(order.customer_phone, msg)
                flash(f"Order {order.order_number} updated to '{new_status}' — WhatsApp sent to customer.", "success")
            else:
                flash(f"Order {order.order_number} updated to '{new_status}'.", "success")

        except Exception as e:
            print(f"WhatsApp error: {e}")
            flash(f"Order updated to '{new_status}' but WhatsApp failed: {e}", "danger")
    else:
        flash(f"Order {order.order_number} status unchanged.", "info")

    # Redirect back to where the request came from
    next_url = request.form.get('next', url_for('admin.dashboard'))
    return redirect(next_url)


# ── SALES DASHBOARD ───────────────────────────────────────────────────────────
@admin_bp.route('/admin/sales')
@login_required
def sales():
    if not current_user.is_admin:
        return redirect(url_for('main.index'))

    now   = datetime.utcnow()
    today = now.date()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # ── Today's stats ─────────────────────────────────────────────────────────
    orders_today = Order.query.filter(
        func.date(Order.created_at) == today
    ).all()
    revenue_today = sum(o.total for o in orders_today if o.payment_status == 'paid')

    # ── This week ─────────────────────────────────────────────────────────────
    orders_week = Order.query.filter(Order.created_at >= week_ago).all()
    revenue_week = sum(o.total for o in orders_week if o.payment_status == 'paid')

    # ── This month ────────────────────────────────────────────────────────────
    orders_month = Order.query.filter(Order.created_at >= month_ago).all()
    revenue_month = sum(o.total for o in orders_month if o.payment_status == 'paid')

    # ── All time ──────────────────────────────────────────────────────────────
    all_orders   = Order.query.all()
    revenue_all  = sum(o.total for o in all_orders if o.payment_status == 'paid')
    total_orders = Order.query.count()
    paid_orders  = Order.query.filter_by(payment_status='paid').count()

    # ── Orders by county ──────────────────────────────────────────────────────
    county_data = db.session.query(
        Order.county,
        func.count(Order.id).label('count'),
        func.sum(Order.total).label('revenue')
    ).group_by(Order.county).order_by(func.count(Order.id).desc()).all()

    # ── Most popular products (by how many times ordered) ─────────────────────
    # Parse items JSON and count product names
    from collections import Counter
    product_counter = Counter()
    for order in all_orders:
        try:
            items = json.loads(order.items)
            for item in items:
                product_counter[item['name']] += item.get('quantity', 1)
        except Exception:
            continue
    top_products = product_counter.most_common(5)

    # ── Recent 20 orders ──────────────────────────────────────────────────────
    recent_orders = Order.query.order_by(Order.id.desc()).limit(20).all()

    # ── Daily revenue for last 7 days (for chart) ─────────────────────────────
    daily_revenue = []
    for i in range(6, -1, -1):
        day = (now - timedelta(days=i)).date()
        day_orders = Order.query.filter(
            func.date(Order.created_at) == day,
            Order.payment_status == 'paid'
        ).all()
        daily_revenue.append({
            'day':     day.strftime('%a'),
            'revenue': sum(o.total for o in day_orders),
            'count':   len(day_orders),
        })

    return render_template('admin/sales.html',
        revenue_today  = revenue_today,
        revenue_week   = revenue_week,
        revenue_month  = revenue_month,
        revenue_all    = revenue_all,
        orders_today   = len(orders_today),
        orders_week    = len(orders_week),
        total_orders   = total_orders,
        paid_orders    = paid_orders,
        county_data    = county_data,
        top_products   = top_products,
        recent_orders  = recent_orders,
        daily_revenue  = daily_revenue,
    )


# ── FIX IMAGE PATHS (one-time utility) ───────────────────────────────────────
@admin_bp.route('/admin/fix-image-paths')
@login_required
def fix_image_paths():
    if not current_user.is_admin:
        return redirect(url_for('main.index'))

    fixed = 0
    for p in Product.query.all():
        if p.image_url:
            original    = p.image_url
            p.image_url = os.path.basename(p.image_url.replace('\\', '/'))
            if p.image_url != original:
                fixed += 1
    for img in ProductImage.query.all():
        if img.url:
            img.url = os.path.basename(img.url.replace('\\', '/'))

    db.session.commit()
    flash(f"Fixed {fixed} image paths.", "success")
    return redirect(url_for('admin.dashboard'))