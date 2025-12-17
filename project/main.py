from flask import Blueprint, render_template, session
from flask_login import login_required, current_user
from . import db,get_db_name
import sqlite3
from random import shuffle
from .classification_hierarchies import label_hierarchy, labels_dict


conn_images = sqlite3.connect(get_db_name())

def extract_images(conn):
    idxs_labels = conn.execute(
        "SELECT picture_id,label FROM labels WHERE user_id = :user_id AND label != 'none'",
        {"user_id":current_user.id}).fetchall()
    shuffle(idxs_labels)
    idxs = [str(x[0]) for x in idxs_labels]
    labels = [x[1] for x in idxs_labels]
    idx2label = {x:y for x,y in zip(idxs,labels)}
    out = conn.execute(
        "SELECT picture,id FROM images WHERE id IN ({})".format(
            ','.join(idxs)
        )).fetchall()

    o = [x[0].decode('utf-8') for x in out]
    idxs = [x[1] for x in out]
    labels = [idx2label[str(x)] for x in idxs]
    return o,labels,idxs

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/profile')
@login_required
def profile():
    with sqlite3.connect(get_db_name()) as conn_images:
        all_images,image_labels,image_idxs = extract_images(conn_images)
        image_labels = [labels_dict[x] for x in image_labels if x != 'none']

        blobs_labels = [
            {'image':x,'label':y,'idx':z}
            for x,y,z in zip(all_images,image_labels,image_idxs)]
        return render_template('profile.html',
                               name=current_user.name,
                               blobs_labels=blobs_labels)

@main.app_context_processor
def inject_globals():
    with sqlite3.connect(get_db_name()) as conn_images:
        rows = conn_images.execute(
            "SELECT DISTINCT collection FROM images WHERE collection IS NOT NULL ORDER BY collection;"
        ).fetchall()
    collections = [r[0] for r in rows if r[0] is not None]
    return {
        "collection": session.get("collection"),
        "collections": collections,
    }
