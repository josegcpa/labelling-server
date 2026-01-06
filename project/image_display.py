import sqlite3
import base64
from flask import Blueprint, render_template, redirect, url_for, request, session, Response, abort
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
    if len(idxs) == 0:
        return 0
    return max(idxs)
        

def extract_images(conn, image_labels, collection: str | None, page: int = 1, per_page: int = 50):
    if collection is not None:
        count_sql = (
            "SELECT COUNT(DISTINCT l.picture_id) "
            "FROM labels l "
            "JOIN images i ON i.id = l.picture_id "
            "WHERE i.collection = ?"
        )
        total = conn.execute(count_sql, [collection]).fetchone()[0]
    else:
        count_sql = "SELECT COUNT(DISTINCT picture_id) FROM labels"
        total = conn.execute(count_sql).fetchone()[0]

    total = int(total or 0)
    max_page = max(1, (total - 1) // per_page + 1) if total > 0 else 1
    offset = (page - 1) * per_page
    
    if page < 1:
        page = 1
    if page > max_page:
        page = max_page

    if collection is not None:
        ids_sql = (
            "SELECT DISTINCT l.picture_id "
            "FROM labels l "
            "JOIN images i ON i.id = l.picture_id "
            "WHERE i.collection = ? "
            "ORDER BY l.picture_id "
            "LIMIT ? OFFSET ?"
        )
        rows = conn.execute(ids_sql, [collection, per_page, offset]).fetchall()
    else:
        ids_sql = (
            "SELECT DISTINCT picture_id "
            "FROM labels "
            "ORDER BY picture_id "
            "LIMIT ? OFFSET ?"
        )
        rows = conn.execute(ids_sql, [per_page, offset]).fetchall()

    picture_ids = [int(r[0]) for r in rows]
    if not picture_ids:
        return {}, total, max_page

    placeholders = ",".join(["?"] * len(picture_ids))
    if collection is not None:
        sql = (
            f"SELECT l.picture_id, l.label, i.picture "
            f"FROM labels l "
            f"JOIN images i ON i.id = l.picture_id "
            f"WHERE l.picture_id IN ({placeholders}) AND i.collection = ? AND l.label != 'none' "
            f"ORDER BY l.picture_id"
        )
        params = [*picture_ids, collection]
    else:
        sql = (
            f"SELECT l.picture_id, l.label, i.picture "
            f"FROM labels l "
            f"JOIN images i ON i.id = l.picture_id "
            f"WHERE l.picture_id IN ({placeholders}) AND l.label != 'none' "
            f"ORDER BY l.picture_id"
        )
        params = list(picture_ids)

    out_rows = conn.execute(sql, params).fetchall()
    output_dict = {str(pid): {'image': None, 'labels': []} for pid in picture_ids}

    for pid, label, imblob in out_rows:
        pid = int(pid)
        pid_key = str(pid)
        if pid_key not in output_dict:
            continue
        if output_dict[pid_key]['image'] is None:
            output_dict[pid_key]['image'] = imblob.decode('utf-8')
        if label in image_labels:
            output_dict[pid_key]['labels'].append(image_labels[label])

    output_dict = {k: v for k, v in output_dict.items() if v['image'] is not None and len(v['labels']) > 0}
    return output_dict, total, max_page

def extract_picture(conn_images, picture_id: int, collection: str | None):
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

def extract_pictures(conn_images, picture_ids: list[int], collection: str | None):
    if not picture_ids:
        return []

    placeholders = ",".join(["?"] * len(picture_ids))
    if collection is not None:
        sql = f"SELECT id, picture, name FROM images WHERE id IN ({placeholders}) AND collection = ?"
        params = [*picture_ids, collection]
    else:
        sql = f"SELECT id, picture, name FROM images WHERE id IN ({placeholders})"
        params = list(picture_ids)
    try:
        cur = conn_images.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        by_id = {int(r[0]): (r[1].decode('utf-8'), r[2]) for r in rows}
        return [by_id.get(int(pid), (0, 0)) for pid in picture_ids]
    except:
        return []


def extract_label(conn_images, picture_id, labels_dict):
    return extract_labels(conn_images, [picture_id], labels_dict)[0]

def extract_labels(conn_images, picture_ids: list[int | None], labels_dict):
    if not picture_ids:
        return []

    valid_picture_ids = [int(pid) for pid in picture_ids if pid is not None]
    if not valid_picture_ids:
        return ["none" for _ in picture_ids]

    placeholders = ",".join(["?"] * len(valid_picture_ids))
    sql = f"SELECT picture_id, label FROM labels WHERE user_id = ? AND picture_id IN ({placeholders})"
    try:
        cur = conn_images.cursor()
        rows = cur.execute(sql, [current_user.id, *valid_picture_ids]).fetchall()
        by_id = {int(r[0]): r[1] for r in rows}
    except:
        by_id = {}

    out = []
    for pid in picture_ids:
        if pid is None:
            out.append("none")
            continue
        label = by_id.get(int(pid), "none")
        if label not in labels_dict:
            label = "none"
        out.append(label)
    return out

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

@image_display.route('/image/<int:picture_id>.png')
@login_required
def image_png(picture_id: int):
    collection = request.args.get('collection', None)
    if collection == "null":
        collection = None
    if collection is None:
        collection = session.get("collection", None)
    with sqlite3.connect(get_db_name()) as conn_images:
        if collection is not None:
            sql = "SELECT picture FROM images WHERE id = :id AND collection = :collection"
            param = {'id': picture_id, 'collection': collection}
        else:
            sql = "SELECT picture FROM images WHERE id = :id"
            param = {'id': picture_id}
        row = conn_images.execute(sql, param).fetchone()
        if row is None:
            abort(404)
        b64_str = row[0].decode('utf-8')
    try:
        img_bytes = base64.b64decode(b64_str)
    except Exception:
        abort(404)
    resp = Response(img_bytes, mimetype='image/png')
    resp.headers['Cache-Control'] = 'public, max-age=43200'
    return resp

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
        idxs = [image_collection_correspondence[collection].get(i - 1, None) for i in idxs]
    with sqlite3.connect(get_db_name()) as conn_images:
        images = extract_pictures(conn_images, idxs, collection)
        image_blobs = [x[0] for x in images]
        names = [x[1] for x in images]

    with sqlite3.connect(get_db_name()) as conn_images:
        labels = extract_labels(conn_images, idxs, labels_dict)
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
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    if per_page < 1:
        per_page = 50
    elif per_page > 200:
        per_page = 200

    with sqlite3.connect(get_db_name()) as conn_images:
        image_dict, total, max_page = extract_images(conn_images, labels_dict, collection, page=page, per_page=per_page)

        return render_template(
            'all-images.html',
            image_dict=image_dict,
            collection=collection,
            page=page,
            max_page=max_page,
            per_page=per_page,
        )

@image_display.route('/collections=<collection>')
@login_required
def set_collection(collection):
    if collection == "null":
        session["collection"] = None
    elif collection in get_unique_collections():
        session["collection"] = collection
    return redirect(url_for('image.images',page=str(1)))
