from app import db
from datetime import datetime, timedelta
import json
from flask_login import UserMixin

# --- USER MODEL FOR ADMIN ACCESS ---
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    __tablename__ = 'products'
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(200), nullable=False)
    category    = db.Column(db.String(50), nullable=False)
    gender      = db.Column(db.String(20), nullable=False)
    price       = db.Column(db.Integer, nullable=False)
    sale_price  = db.Column(db.Integer, nullable=True)
    description = db.Column(db.Text, nullable=True)
    sizes       = db.Column(db.String(200), nullable=True) 
    stock       = db.Column(db.Integer, default=0)
    is_featured = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    # --- MULTIPLE IMAGES RELATIONSHIP ---
    # This allows a single product to have a list of images.
    # cascade="all, delete-orphan" means if you delete a product, its photos are deleted too.
    images = db.relationship('ProductImage', backref='product', lazy=True, cascade="all, delete-orphan")

    # This remains as the 'Main' thumbnail (the first image uploaded)
    image_url   = db.Column(db.String(500), nullable=True)

    def size_list(self):
        if self.sizes:
            return [s.strip() for s in self.sizes.split(',')]
        return []

# --- PRODUCT IMAGE MODEL ---
class ProductImage(db.Model):
    __tablename__ = 'product_images'
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)

class Order(db.Model):
    __tablename__ = 'orders'
    id               = db.Column(db.Integer, primary_key=True)
    order_number     = db.Column(db.String(20), unique=True, nullable=False)
    customer_name    = db.Column(db.String(200), nullable=False)
    customer_phone   = db.Column(db.String(20), nullable=False)
    delivery_address = db.Column(db.String(500), nullable=False)
    county           = db.Column(db.String(50), nullable=False)
    items            = db.Column(db.Text, nullable=False) 
    subtotal         = db.Column(db.Integer, nullable=False)
    delivery_fee     = db.Column(db.Integer, nullable=False)
    total            = db.Column(db.Integer, nullable=False)
    payment_status   = db.Column(db.String(20), default='pending')
    order_status     = db.Column(db.String(20), default='pending')
    
    checkout_request_id = db.Column(db.String(100), nullable=True)
    mpesa_receipt       = db.Column(db.String(20), nullable=True)
    
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    def get_whatsapp_items(self):
        try:
            data = json.loads(self.items)
            return "\n".join([f"• {item['name']} ({item['size']})" for item in data])
        except:
            lines = self.items.split(',')
            return "\n".join([f"• {line.strip()}" for line in lines])

    def get_delivery_date(self):
        future_date = self.created_at + timedelta(days=3)
        return future_date.strftime('%A, %d %b')

class PaymentLog(db.Model):
    __tablename__ = 'payment_logs'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    result_code = db.Column(db.Integer, nullable=True)
    result_description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)