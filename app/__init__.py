from flask import Flask
from flask_mysqldb import MySQL

mysql = MySQL()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # Initialize MySQL
    mysql.init_app(app)

    # Attach MySQL to the app instance
    app.mysql = mysql

    # Register Blueprints
    from .auth import auth_bp
    from .routes import routes_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(routes_bp)

    return app
