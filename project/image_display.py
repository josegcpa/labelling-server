import sqlite3
from flask import Blueprint, render_template, redirect, url_for, request, session
from flask_login import login_required, current_user
from . import db,get_db_name
from .classification_hierarchies import label_hierarchy, labels_dict
from .models import User

n_images = 16

def get_image_collection_correspondence():
    with sqlite3.connect(get_db_name()) as conn_images:
        rows = conn_images.execute(
            "SELECT id, collection FROM images;"
        ).fetchall()
    collection_count = {k[1]: 0 for k in rows}
    icl = {k[1]: {} for k in rows}
    for row in rows:
        curr_c = collection_count[row[1]]
        icl[row[1]][curr_c] = row[0]
        collection_count[row[1]] += 1
    return icl

image_collection_correspondence = get_image_collection_correspondence()

def get_collection_count(collection: str) -> int:
    with sqlite3.connect(get_db_name()) as conn_images:
        if collection is None:
            ex = conn_images.execute("SELECT COUNT(*) FROM images")
        else:
            ex = conn_images.execute(
                "SELECT COUNT(*) FROM images WHERE collection = :collection;",
                {"collection": collection},
            )
        row = ex.fetchone()
    return int(row[0] if row is not None else 0)

def get_unique_collections() -> list[str]:
    with sqlite3.connect(get_db_name()) as conn_images:
        rows = conn_images.execute(
            "SELECT DISTINCT collection FROM images WHERE collection IS NOT NULL ORDER BY collection;"
        ).fetchall()
    collections = [r[0] for r in rows if r[0] is not None]
    return collections

def update_n_labelled_images():
    with sqlite3.connect(get_db_name()) as conn_images:
        idxs_labels = conn_images.execute(
            "SELECT picture_id,label FROM labels WHERE user_id = :user_id",
            {'user_id':current_user.id}
            ).fetchall()

        user = User.query.filter_by(email=current_user.email).first()
        user.n_cells = len(idxs_labels)
    db.session.commit()
    
def get_first_with_no_label():
    user_id = current_user.id
    with sqlite3.connect(get_db_name()) as conn:
        idxs = conn.execute(
            "SELECT picture_id FROM labels WHERE user_id = :user_id", 
            {"user_id": user_id})
    idxs = [x[0] for x in idxs]
    return max(idxs)
        

def extract_images(conn, image_labels, collection: str | None):
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

    if collection is not None:
        sql_statement = "SELECT picture,id FROM images WHERE id IN ({}) AND collection = :collection".format(
            ','.join(idxs)
        )
        out = conn.execute(sql_statement, {'collection': collection}).fetchall()
    else:
        sql_statement = "SELECT picture,id FROM images WHERE id IN ({})".format(
            ','.join(idxs)
        )
        out = conn.execute(sql_statement).fetchall()

    o = {str(x[1]): x[0].decode('utf-8') for x in out}
    output_dict = {}

    for i in idxs:
        if i in o:
            l = [image_labels[x] for x in idx2labels[i] if x != 'none']
            if len(l) == 0:
                continue
            output_dict[i] = {
                'image': o[i],
                'labels': [image_labels[x] for x in idx2labels[i] if x != 'none']
            }
    return output_dict

def extract_picture(conn, picture_id: int, collection: str | None):
    with sqlite3.connect(get_db_name()) as conn_images:
        if collection is not None:
            sql = "SELECT picture, name FROM images WHERE id = :id AND collection = :collection"
            param = {'id': picture_id, 'collection': collection}
        else:
            sql = "SELECT picture, name FROM images WHERE id = :id"
            param = {'id': picture_id}
        try:
            cur = conn_images.cursor()
            cur.execute(sql, param)
            ablob, name = cur.fetchone()
            return ablob.decode('utf-8'),name
        except:
            return 0,0

def extract_label(conn, picture_id, labels_dict):
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
    global image_collection_correspondence
    collection = session.get("collection", None)
    if request.args.get('collection'):
        collection = request.args.get('collection')
    if collection == "null":
        collection = None
    if current_user.is_authorised == False:
        return no_authorisation()
    page = int(page)
    max_page_images = get_collection_count(collection) // n_images + 1
    if page > max_page_images:
        return redirect(url_for('image.images',page=str(max_page_images)))
    if page < 1:
        return redirect(url_for('image.images',page=str(1)))
    page_offset = (page-1) * n_images
    idxs = [i + page_offset for i in range(1, n_images+1)]
    if collection is not None:
        if collection not in image_collection_correspondence:
            image_collection_correspondence = get_image_collection_correspondence()
        idxs = [image_collection_correspondence[collection].get(i - 1, None) for i in idxs]
    with sqlite3.connect(get_db_name()) as conn_images:
        images = [extract_picture(conn_images, i, collection)
                  for i in idxs]
        image_blobs = [x[0] for x in images]
        names = [x[1] for x in images]

    with sqlite3.connect(get_db_name()) as conn_images:
        labels = [extract_label(conn_images,i,labels_dict) for i in idxs]
    first_no_label = get_first_with_no_label() // (n_images)

    return render_template(
        'displayer-images.html',
        name=current_user.name,
        image_blobs=image_blobs,
        page=page,
        max_page=max_page_images,
        names=names,
        labels=labels,
        image_hierarchy=label_hierarchy,
        first_no_label=first_no_label,
        image_idxs=idxs)

@image_display.route('/images-all')
@login_required
def images_all():
    collection = session.get("collection", None)
    if current_user.is_authorised == False:
        return no_authorisation()
    with sqlite3.connect(get_db_name()) as conn_images:
        image_dict = extract_images(conn_images, labels_dict, collection)

        return render_template('all-images.html',
                               image_dict=image_dict)

@image_display.route('/collections=<collection>')
@login_required
def set_collection(collection):
    if collection == "null":
        session["collection"] = None
    elif collection in get_unique_collections():
        session["collection"] = collection
    return redirect(url_for('image.images',page=str(1)))
