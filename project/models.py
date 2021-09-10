from flask_login import UserMixin
from . import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    institute = db.Column(db.String(1000))
    n_cells = db.Column(db.Integer)
    is_admin = db.Column(db.Boolean)
    is_authorised = db.Column(db.Boolean)
