from app import create_app, db
from app.models import Product

app = create_app()
with app.app_context():
    # Force fix the 2 products in your screenshot
    p1 = Product.query.filter_by(name='Pink Air Force 1').first()
    if p1:
        p1.image_file = 'black-work-graphic-tee.jpg' # Use this since you have it
    
    p2 = Product.query.filter_by(name='Striped Rugby Polo').first()
    if p2:
        p2.image_file = 'striped-rugby-polo.jpg'
        
    db.session.commit()
    print("Database force-synced. Restart your server now!")