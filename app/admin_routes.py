import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import Product, ProductImage, Order # Added Order
from app.whatsapp_client import send_shipping_notification # Added for status updates

# Use the 'admin' name you registered in __init__.py
admin_bp = Blueprint('admin', __name__)

# Allowed image extensions helper
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- 1. ADMIN DASHBOARD ---
@admin_bp.route('/admin/dashboard')
@login_required
def dashboard():
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for('main.index'))
    
    # Fetch all orders and products for the control panel
    orders = Order.query.order_by(Order.created_at.desc()).all()
    products = Product.query.order_by(Product.created_at.desc()).all()
    
    # Calculate quick stats for the dashboard header
    total_sales = sum(order.total for order in orders if order.payment_status == 'paid')
    
    return render_template('admin/dashboard.html', 
                           orders=orders, 
                           products=products, 
                           total_sales=total_sales)

# --- 2. UPDATE ORDER STATUS ---
@admin_bp.route('/admin/order/<int:order_id>/status', methods=['POST'])
@login_required
def update_order_status(order_id):
    if not current_user.is_admin:
        return redirect(url_for('main.index'))
        
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    
    order.payment_status = new_status
    db.session.commit()
    
    # If you mark an order as 'shipped', trigger the WhatsApp notification
    if new_status == 'shipped':
        try:
            send_shipping_notification(order)
            flash(f"Order {order.order_number} marked as shipped and customer notified!", "success")
        except Exception as e:
            flash(f"Status updated, but WhatsApp failed: {str(e)}", "warning")
    else:
        flash(f"Order {order.order_number} status updated to {new_status}.", "info")
        
    return redirect(url_for('admin.dashboard'))

# --- 3. ADD PRODUCT (WITH MULTI-PHOTO UPLOAD) ---
@admin_bp.route('/admin/add-product', methods=['GET', 'POST'])
@login_required
def add_product():
    if not current_user.is_admin:
        flash("Unauthorized access! Admins only.", "danger")
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        try:
            # Create the Product base info
            new_product = Product(
                name=request.form.get('name'),
                price=int(request.form.get('price')),
                sizes=request.form.get('sizes'),
                stock=int(request.form.get('stock', 1)),
                description=request.form.get('description'),
                category=request.form.get('category', 'General'), 
                gender=request.form.get('gender', 'Unisex')
            )
            
            db.session.add(new_product)
            db.session.flush() 

            # Process Multi-Photo Uploads
            files = request.files.getlist('photos')
            
            upload_count = 0
            for i, file in enumerate(files[:5]): # Limit to 5 images
                if file and file.filename != '' and allowed_file(file.filename):
                    ext = os.path.splitext(file.filename)[1].lower()
                    filename = f"{uuid.uuid4().hex}{ext}"
                    
                    save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    file.save(save_path)
                    
                    img_url = f"/static/uploads/{filename}"
                    
                    if upload_count == 0:
                        new_product.image_url = img_url
                    
                    new_img = ProductImage(url=img_url, product_id=new_product.id)
                    db.session.add(new_img)
                    upload_count += 1

            if upload_count == 0:
                flash("Product added, but no images were uploaded.", "warning")
            else:
                db.session.commit()
                flash(f"Successfully added {new_product.name}!", "success")
            
            return redirect(url_for('admin.dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error adding product: {str(e)}", "danger")
            return redirect(url_for('admin.add_product'))

    return render_template('add_product.html')