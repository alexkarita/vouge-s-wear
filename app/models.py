from app import db
from datetime import datetime

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
    image_url   = db.Column(db.String(500), nullable=True)
    stock       = db.Column(db.Integer, default=0)
    is_featured = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def size_list(self):
        if self.sizes:
            return [s.strip() for s in self.sizes.split(',')]
        return []

    def __repr__(self):
        return f'<Product {self.name}>'
    