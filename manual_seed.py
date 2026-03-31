from app import create_app, db
from app.models import Product

app = create_app()

with app.app_context():
    db.session.query(Product).delete()
    
    full_inventory = [
        Product(name='Striped Rugby Polo', price=900, category='clothes', gender='unisex', is_featured=True, image_url='/static/uploads/striped-rugby-polo.jpg.jpeg'),
        Product(name='Black Work Jersey', price=1200, category='clothes', gender='men', is_featured=True, image_url='/static/uploads/black-work-jers.jpg'),
        Product(name='Heart Zip Pullover', price=1500, category='clothes', gender='unisex', is_featured=True, image_url='/static/uploads/heart-zip-pullov.jpg'),
        Product(name='Nike Dunk Olive', price=4500, category='shoes', gender='unisex', is_featured=True, image_url='/static/uploads/nike-dunk-olive.jpg'),
        Product(name='Vintage Graphic Tee', price=800, category='clothes', gender='unisex', is_featured=True, image_url='/static/uploads/vintage-tee.jpg'),
        Product(name='Cargo Pants Black', price=1800, category='clothes', gender='men', is_featured=True, image_url='/static/uploads/cargo-pants.jpg'),
        Product(name='Classic White Sneakers', price=3200, category='shoes', gender='unisex', is_featured=True, image_url='/static/uploads/white-sneaks.jpg')
    ]
    
    db.session.add_all(full_inventory)
    db.session.commit()
    print("✅ All 7 products restored to the vault!")