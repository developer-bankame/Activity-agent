from flask import Flask
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Import and register blueprints, if any
    # from app.routes import main_bp
    # app.register_blueprint(main_bp)
    
    return app
