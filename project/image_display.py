from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user
from . import db,get_db_name
from .classification_hierarchies import *
from .models import User
import sqlite3

n_cols = 4
n_rows = 4

def update_n_labelled_images():
    with sqlite3.connect(get_db_name()) as conn_images:
        idxs_labels = conn_images.execute(
            "SELECT picture_id,label FROM labels WHERE user_id = :user_id",
            {'user_id':current_user.id}
            ).fetchall()

        user = User.query.filter_by(email=current_user.email).first()
        user.n_cells = len(idxs_labels)
    db.session.commit()

def extract_images(conn,image_labels):
    idxs_labels = conn.execute(
        "SELECT picture_id,label FROM labels"
        ).fetchall()
    idxs = [str(x[0]) for x in idxs_labels]
    labels = [x[1] for x in idxs_labels]
    idx2labels = {}
    for x,y in zip(idxs,labels):
        if x in idx2labels:
            idx2labels[x].append(y)
        else:
            idx2labels[x] = [y]
    idxs = list(idx2labels.keys())

    out = conn.execute(
        "SELECT picture,id FROM images WHERE id IN ({})".format(
            ','.join(idxs)
        )).fetchall()

    o = [x[0].decode('utf-8') for x in out]
    output_dict = {}

    for i,img in zip(idxs,o):
        output_dict[i] = {
            'image':img,
            'labels':[image_labels[x] for x in idx2labels[i] if x != 'none']
        }
    return output_dict

def extract_picture(conn,picture_id):
    with sqlite3.connect(get_db_name()) as conn_images:
        sql = "SELECT picture, name FROM images WHERE id = :id"
        param = {'id': picture_id}
        try:
            cur = conn_images.cursor()
            cur.execute(sql,param)
            ablob, name = cur.fetchone()
            return ablob.decode('utf-8'),name
        except:
            return 0,0

def extract_label(conn,picture_id,labels_dict):
    with sqlite3.connect(get_db_name()) as conn_images:
        sql = "SELECT label FROM labels WHERE picture_id = :picture_id AND user_id = :user_id"
        param = {
            'picture_id':picture_id,
            'user_id':current_user.id}
        cur = conn_images.cursor()
        cur = cur.execute(sql,param)
        o = cur.fetchone()

        if o is None:
            o = "none"
        else:
            o = o[0]
        if o not in labels_dict:
            o = "none"

        return o

def insert_label(conn,picture_id,label):
    sql = 'SELECT label FROM labels WHERE picture_id = :picture_id AND user_id = :user_id;'
    param = {
        'picture_id':picture_id,
        'user_id':current_user.id}
    cur = conn.cursor()
    if cur.execute(sql,param).fetchone():
        sql = 'UPDATE labels SET label = :label WHERE picture_id = :picture_id AND user_id = :user_id;'
    else:
        sql = 'INSERT INTO labels (picture_id, label, user_id) VALUES (:picture_id, :label, :user_id);'
    param['label'] = label
    cur = conn.cursor()
    cur.execute(sql,param)
    db.session.commit()

with sqlite3.connect(get_db_name()) as conn_images:
    cur_images = conn_images.cursor()
    n_images = cur_images.execute(
        "SELECT COUNT(*) FROM images;").fetchone()[0]

max_page_images = n_images // (n_cols * n_rows) + 1

image_display = Blueprint('image', __name__)

# No authorisation routing

@image_display.route('/no-authorisation')
@login_required
def no_authorisation():
    return render_template('no-authorisation.html')

# Serving images

@image_display.route('/images_label',methods=['POST'])
@login_required
def get_images_label():
    with sqlite3.connect(get_db_name()) as conn_images:
        jsdata = request.form
        label = jsdata['label']
        form_id = jsdata['form_id']
        picture_id = int(form_id[10:])
        insert_label(conn_images,picture_id,label)
    update_n_labelled_images()
    return jsdata

@image_display.route('/images=<page>')
@login_required
def images(page):
    if current_user.is_authorised == False:
        return no_authorisation()
    page = int(page)
    if page > max_page_images:
        return redirect(url_for('image.images',page=str(max_page_images)))
    if page < 1:
        return redirect(url_for('image.images',page=str(1)))
    page_offset = (page-1) * n_cols * n_rows
    idxs = [i + page_offset for i in range(1,n_cols*n_rows+1)]
    images = [extract_picture(conn_images,i)
              for i in idxs]
    image_blobs = [x[0] for x in images]
    names = [x[1] for x in images]

    labels = [extract_label(conn_images,i,labels_dict) for i in idxs]

    return render_template(
        'displayer-images.html',
        name=current_user.name,
        n_cols=n_cols,
        n_rows=n_rows,
        image_blobs=image_blobs,
        page=page,
        max_page=max_page_images,
        names=names,
        labels=labels,
        image_hierarchy=label_hierarchy,
        image_idxs=idxs)

@image_display.route('/images-all')
@login_required
def images_all():
    with sqlite3.connect(get_db_name()) as conn_images:
        if current_user.is_authorised == False:
            return no_authorisation()
        image_dict = extract_images(conn_images,labels_dict)

        return render_template('all-images.html',
                               image_dict=image_dict)
