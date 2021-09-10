from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

def get_db_name():
    with open("db_name") as o:
        return o.readlines()[0].strip()

# init SQLAlchemy so we can use it later in our models
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = b'1Fcxk9$kZm6c1pyfAXjjXrwn*egDFJl1Rqf9Ui!yN4$UbY%p0$'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        # since the user_id is just the primary key of our user table, use it in the query for the user
        return User.query.get(int(user_id))

    # blueprint for auth routes in our app
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    # blueprint for non-auth parts of app
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .image_display import image_display as image_blueprint
    app.register_blueprint(image_blueprint)

    from .admin import admin_blueprint as admin_blueprint
    app.register_blueprint(admin_blueprint)

    return app
