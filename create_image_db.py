import sqlite3
from PIL import Image, ImageDraw
import os
import base64
import random
import numpy as np
from io import BytesIO
from glob import glob
from tqdm import tqdm

MAX_HEIGHT = 15000
MAX_WIDTH = 20000

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Create SQLite image database.')
    parser.add_argument('--input_path',dest="input_path",type=str,
                        help='path to folder containing images')
    parser.add_argument('--output_path',dest="output_path",type=str,
                        help='path to SQLite output')
    parser.add_argument('--add_dot',dest="add_dot",action="store_true",
                        help='adds small green dot to center of image')
    parser.add_argument('--overwrite',dest="overwrite",action="store_true",
                        help='overwrites db')
    parser.add_argument('--increment', dest='increment',action="store_true",
                        help="adds to db")
    parser.add_argument('--seed', dest='seed', type=int, default=42,
                        help="seed for image shuffling")
    args = parser.parse_args()

    conn = sqlite3.connect(args.output_path)

    if os.path.exists(args.output_path):
        if args.increment is True:
            print("adding to db")
        elif args.overwrite is False:
            print("db file already exists, to overwrite add --overwrite")
            exit()

    sql = '''
    create table if not exists images(
        id integer primary key autoincrement,
        picture blob,
        name text);
    '''
    conn.execute(sql)

    sql = '''
    create table if not exists labels(
        id integer primary key autoincrement,
        picture_id integer,
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

    rng = np.random.default_rng(args.seed)

    i = 0
    images = sorted(glob(args.input_path + '/*'))
    rng.shuffle(images)
    for image_path in tqdm(images):
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
        if args.add_dot:
            h,w = image.size
            offset = 3
            center_x, center_y = (h // 2, w // 2)
            draw = ImageDraw.Draw(image)
            draw.rectangle([
                (center_x - offset,center_y - offset),
                (center_x + offset,center_y + offset)], 
                fill=(0, 255, 0))
    
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
