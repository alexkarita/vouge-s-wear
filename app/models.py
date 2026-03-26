from app import db
from datetime import datetime
import json

class Product(db.Model):
    __tablename__ = 'products'
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(200), nullable=False)
    category    = db.Column(db.String(50), nullable=False)
    gender      = db.Column(db.String(20), nullable=False)
    price       = db.Column(db.Integer, nullable=False)
    sale_price  = db.Column(db.Integer, nullable=True)
    description = db.Column(db.Text, nullable=True)
    sizes       = db.Column(db.String(200), nullable=True) # Stores "S,M,L"
    image_url   = db.Column(db.String(500), nullable=True)
    stock       = db.Column(db.Integer, default=0)
    is_featured = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    # HELPER FUNCTION: Turns the "sizes" string into a list for the website buttons
    def size_list(self):
        if self.sizes:
            # Splits "S, M, L" into ['S', 'M', 'L']
            return [s.strip() for s in self.sizes.split(',')]
        return []

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
    
    # M-PESA TRACKING FIELDS
    checkout_request_id = db.Column(db.String(100), nullable=True)
    mpesa_receipt       = db.Column(db.String(20), nullable=True)
    
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

class PaymentLog(db.Model):
    __tablename__ = 'payment_logs'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    result_code = db.Column(db.Integer, nullable=True)
    result_description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)