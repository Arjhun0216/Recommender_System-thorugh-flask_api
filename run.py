# run.py
from app import create_app, db
from app.models import User, Item, Interaction, Recommendation

app = create_app("development")

def init_db():
    """Creates all database tables based on models.py"""
    with app.app_context():
        db.create_all()
        print("✅ All tables created successfully!")
        print("   - users")
        print("   - items")
        print("   - interactions")
        print("   - recommendations")

if __name__ == "__main__":
    init_db()  # Create tables first
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )