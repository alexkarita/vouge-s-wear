from app import create_app, db
from app.models import Product

app = create_app()

with app.app_context():
    print("--- Fixing Database Column: image_url ---")
    
    # Matching your exact folder filenames to your products
    image_map = {
        'Pink Air Force 1': 'lv-trainer-pink.jpg.jpeg',
        'Striped Rugby Polo': 'striped-rugby-polo.jpg.jpeg',
        'Black Work Graphic Shirt': 'black-work-jersey.jpg.jpeg',
        'White Black Half Zip Polo': 'heart-zip-pullover.jpg.jpeg',
        'Nike Air Jordan 1 Low': 'nike-dunk-olive.jpg.jpeg',
        'Classic Vogue Tee': 'black-work-jersey.jpg.jpeg'
    }

    products = Product.query.all()

    for p in products:
        if p.name in image_map:
            # We are using image_url because that is what is in your models.py!
            p.image_url = image_map[p.name]
            print(f"✅ FIXED: {p.name} -> {p.image_url}")
    
    db.session.commit()
    print("--- SUCCESS: Database synced ---")