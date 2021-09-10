from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User
from . import db
import re

email_regex = re.compile(r"[^@]+@[^@]+\.[^@]+")

auth = Blueprint('auth', __name__)

@auth.route('/login')
def login():
    if current_user.is_authenticated == True:
        return redirect(url_for('main.profile'))
    return render_template('login.html')

@auth.route('/signup-successful')
def signup_successful():
    if current_user.is_authenticated == True:
        return redirect(url_for('main.profile'))
    return render_template('signup-successful.html')

@auth.route('/signup')
def signup():
    if current_user.is_authenticated == True:
        return redirect(url_for('main.profile'))
    return render_template('signup.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@auth.route('/signup', methods=['POST'])
def signup_post():
    email = request.form.get('email')
    name = request.form.get('name')
    institute = request.form.get('institute')
    password = request.form.get('password')

    if len(password) < 8: # checks password length
        flash('Password too short')
        return redirect(url_for('auth.signup'))
    if email_regex.match(email) is None:
        flash('Email is not valid')
        return redirect(url_for('auth.signup'))
    if len(institute) < 2:
        flash('Institute name is too short')
        return redirect(url_for('auth.signup'))

    User.query.filter_by(email=email).first()
    user = User.query.filter_by(email=email).first()

    if user: # checks if user exists
        flash('Email address already exists')
        return redirect(url_for('auth.signup'))

    new_user = User(
        email=email, name=name,
        password=generate_password_hash(password, method='sha256'),
        institute=institute,n_cells=0,is_admin=False,is_authorised=False)

    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for('auth.signup_successful'))

@auth.route('/login',methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')

    user = User.query.filter_by(email=email).first()

    # check if the user actually exists
    if not user or not check_password_hash(user.password, password):
        flash('Please check your login details and try again.')
        return redirect(url_for('auth.login')) # if the user doesn't exist or password is wrong, reload the page
    if user.is_authorised == False:
        flash("""
              Please wait for admin authorisation.
              """)
        return redirect(url_for('auth.login'))

    # if the above check passes, then we know the user has the right credentials
    login_user(user)
    return redirect(url_for('main.profile'))
