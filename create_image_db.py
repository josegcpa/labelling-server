import sqlite3
from PIL import Image
import os
import base64
import random
import argparse
import numpy as np
from io import BytesIO
from glob import glob
from tqdm import tqdm

MAX_HEIGHT = 15000
MAX_WIDTH = 20000

parser = argparse.ArgumentParser(description='Create SQLite image database.')
parser.add_argument('--input_path',dest="input_path",type=str,
                    help='path to folder containing images')
parser.add_argument('--output_path',dest="output_path",type=str,
                    help='path to SQLite output')
args = parser.parse_args()

conn = sqlite3.connect(args.output_path)

try:
    conn.execute("DROP TABLE images;")
    conn.execute("DROP TABLE slide_labels;")
    conn.execute("DROP TABLE metadata;")
    conn.execute("DROP TABLE labels;")
except:
    pass

sql = '''
create table if not exists images(
    id integer primary key autoincrement,
    picture blob,
    name text);
'''
conn.execute(sql)

sql = '''
create table if not exists labels(
    picture_id integer primary key,
    label text,
    user_id text);
'''
conn.execute(sql)

sql ='''
create table if not exists metadata(
    id integer primary key autoincrement,
    number_of_images integer);
'''
conn.execute(sql)

i = 0
for image_path in tqdm(glob(args.input_path + '/*')):
    image = Image.open(image_path)
    if image.size[0] > MAX_HEIGHT:
        rescale_factor = image.size[0] / MAX_HEIGHT
        size = [0,0]
        size[0] = MAX_HEIGHT
        size[1] = int(image.size[1]/rescale_factor)
        image = image.resize(size)
    if image.size[1] > MAX_WIDTH:
        rescale_factor = image.size[1] / MAX_WIDTH
        size = [0,0]
        size[1] = MAX_WIDTH
        size[0] = int(image.size[0]/rescale_factor)
        image = image.resize(size)
   
    i += 1
    with BytesIO() as bio:
        image.save(bio,format='JPEG')

        ablob = base64.b64encode(bio.getvalue())
        sql = '''INSERT INTO images
        (picture, name)
        VALUES(?, ?);'''
        conn.execute(sql,[sqlite3.Binary(ablob), image_path])
        conn.commit()

sql = '''INSERT INTO metadata
(number_of_images)
VALUES(?);'''
conn.execute(sql,[i])
conn.commit()
