from app import app, db
from app.models import Product

with app.app_context():
    print("--- Starting Database Sync ---")
    
    # 1. Update Pink Air Force 1
    p1 = Product.query.filter_by(name="Pink Air Force 1").first()
    if p1:
        p1.image_url = "/static/uploads/lv-trainer-pink.jpg.jpeg"
        print("Updated Pink Air Force 1")

    # 2. Update Striped Rugby Polo
    p2 = Product.query.filter_by(name="Striped Rugby Polo").first()
    if p2:
        p2.image_url = "/static/uploads/striped-rugby-polo.jpg.jpeg"
        print("Updated Striped Rugby Polo")

    # 3. Update Black Work Graphic Shirt
    p3 = Product.query.filter_by(name="Black Work Graphic Shirt").first()
    if p3:
        p3.image_url = "/static/uploads/black-work-jersey.jpg.jpeg"
        print("Updated Black Work Jersey")

    db.session.commit()
    print("--- All products synced! Refresh your browser. ---")