# run.py
import os
from app import create_app, db
from app.models import User, Item, Interaction, Recommendation, Developer

config_name = os.getenv("FLASK_ENV", "development")
app = create_app(config_name)

def init_db():
    with app.app_context():
        db.create_all()
        print("✅ All tables created!")

if __name__ == "__main__":
    init_db()
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )