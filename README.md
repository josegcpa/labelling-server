# Labelling server

This is a very simple (and hopefully intuitive!) local server to label images using Python (flask, sqlite3), Bootstrap and js.

To use this all you have to is:

1. Install python/virtual envioronment with the packages in in `requirements.txt` using pip

2. Initialise an image database using `create_image_db.py`; here I use the images in `images` and run with it: `python3 create_image_db.py --input_path images --output_path $(cat db_name)`

3. Initialise the user database using `init_db.py`

4. Run the labeller using `sh run_app_local.sh`

5. Create an account in the platform and activate + set as admin inside of sqlite3: connect to this database using sqlite3 through `sqlite3 project/db.sqlite` and set your user as authorised and as admin (`UPDATE user SET is_admin=1,is_authorised=1 WHERE email="<whatever e-mail you used to register>"`)

6. Login and start labelling! 

This renders you pretty much good to go. As usual and since this is Flask, and will be running on port 5000 of a local host (in this case, `run_app_local.sh` uses 0.0.0.0; so access your local platform through 0.0.0.0:5000). 
