export LC_ALL=en_GB.UTF-8
export LANG=en_GB.UTF-8
export FLASK_APP=project
export FLASK_ENV=deployment
export FLASK_DEBUG=1
export FLASK_RUN_HOST=0.0.0.0

python3 -m flask run --host=0.0.0.0
