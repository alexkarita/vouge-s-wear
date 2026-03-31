from app import create_app, db
from app.models import Product

# This starts your Flask app settings
app = create_app()

def add_items_back():
    with app.app_context():
        # This adds one product so we can see if the fix worked
        p1 = Product(
            name="Classic Vogue Tee",
            category="Clothes",
            gender="Unisex",
            price=2500,
            image_url="product1.jpg", 
            is_featured=True, # This is the "magic" column that was crashing
            stock=20,
            description="Premium quality signature wear."
        )
        
        db.session.add(p1)
        db.session.commit()
        print("Done! Product added back to the database.")

if __name__ == "__main__":
    add_items_back()