export LC_ALL=en_GB.UTF-8
export LANG=en_GB.UTF-8
export FLASK_APP=project
export FLASK_ENV=deployment
export FLASK_DEBUG=1
export FLASK_RUN_HOST=0.0.0.0
export FLASK_RUN_PORT=5123

uv run flask run --host=0.0.0.0
