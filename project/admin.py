from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User
from . import db
import re

email_regex = re.compile(r"[^@]+@[^@]+\.[^@]+")

admin_blueprint = Blueprint('admin', __name__)

@admin_blueprint.route('/admin')
@login_required
def admin():
    if current_user.is_admin == False:
        return redirect(url_for('main.profile'))
    user = User.query.all()
    return render_template('admin.html',user_list=user)

@admin_blueprint.route('/admin/toggle_authorisation',methods=["POST"])
@login_required
def toggle_authorisation():
    if current_user.is_admin == False:
        return redirect(url_for('main.profile'))
    user = User.query.filter_by(id=request.form['user_id']).first()

    if user.is_authorised == True:
        user.is_authorised = False
    else:
        user.is_authorised = True
    db.session.commit()
    return admin()

@admin_blueprint.route('/admin/toggle_admin',methods=["POST"])
@login_required
def toggle_admin():
    if current_user.is_admin == False:
        return redirect(url_for('main.profile'))
    user = User.query.filter_by(id=request.form['user_id']).first()

    if user.is_admin == True:
        user.is_admin = False
    else:
        user.is_admin = True
    db.session.commit()
    return admin()
