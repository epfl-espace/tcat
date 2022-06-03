import io
import os
import json
import re
import subprocess
import threading
import time
import zipfile
from operator import and_, or_
from time import sleep
from datetime import datetime
import uuid
import base64
import mimetypes

from flask import Flask, request, render_template, session, redirect, flash, make_response, send_file
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash

import inputparams
from models import db, User, Configuration, ConfigurationRun
from sqlalchemy import asc, desc
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from dotenv import load_dotenv

load_dotenv()  # sets values from .env file as environment vars

BASE_FOLDER = os.getenv('BASE_FOLDER')
UPLOAD_FOLDER = os.path.join(BASE_FOLDER, 'uploads/')
CONFIG_FOLDER = os.path.join(BASE_FOLDER, 'configs/')
TCAT_DATA = os.path.join(BASE_FOLDER, 'tcat-data/')
TCAT_DIR = os.getenv('TCAT_DIR')
TCAT_PYTHON_EXE = os.getenv('TCAT_PYTHON_EXE')
TCAT_RUN_FILE = os.path.join(TCAT_DIR, os.getenv('TCAT_RUN_FILE'))
ALLOWED_EXTENSIONS = os.getenv('ALLOWED_EXTENSIONS').split(',')
PLOT_IMAGE_NAMES = os.getenv('PLOT_IMAGE_NAMES').split(',')
LOG_FILENAME = os.getenv('LOG_FILENAME')
RESULT_FILENAME = os.getenv('RESULT_FILENAME')
MAX_FILE_LOAD_DURATION_IN_SEC = int(os.getenv('MAX_FILE_LOAD_DURATION_IN_SEC'))


def add_user(username, password, email):
    user = User(username=username, password_hash=generate_password_hash(password), email=email)
    db.session.add(user)
    db.session.commit()


def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv('APP_SECRET')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    with app.app_context():
        db.init_app(app)
        db.create_all()
        session_factory = sessionmaker(bind=db.engine)
        Session = scoped_session(session_factory)

    return app, Session


app, Session = create_app()


def get_data_path(scenario_id, config_run_id):
    return os.path.join(TCAT_DATA, scenario_id, str(config_run_id))


def popen_and_call(on_exit, on_error, config_run_id, wd, popen_args):
    def run_in_thread(on_exit, on_error, config_run_id, wd, popen_args):
        try:
            subprocess.check_output(popen_args, cwd=wd)
        except subprocess.CalledProcessError:
            return on_error(config_run_id)
        else:
            return on_exit(config_run_id)

    thread = threading.Thread(target=run_in_thread, args=(on_exit, on_error, config_run_id, wd, popen_args))
    thread.start()
    # returns immediately after the thread starts
    return thread


def finished_config_run(config_run_id):
    db_session = Session()
    config_run = db_session.query(ConfigurationRun).filter_by(id=config_run_id).first()
    config_run.finished_date = datetime.utcnow()
    config_run.status = 'FINISHED'
    db_session.commit()
    Session.remove()
    return


def failed_config_run(config_run_id):
    db_session = Session()
    config_run = db_session.query(ConfigurationRun).filter_by(id=config_run_id).first()
    config_run.failed_date = datetime.utcnow()
    config_run.status = 'FAILED'
    db_session.commit()
    Session.remove()
    return


def get_current_user():
    if not logged_in():
        return None
    user = User.query.filter_by(username=session['username']).first()
    return user


def logged_in():
    if 'username' in session:
        return True
    return False


def log_the_user_in(username):
    session['username'] = username
    return redirect('index')


def valid_login(username, password):
    user = User.query.filter_by(username=username).first()
    if user is None:
        return False
    return user.verify_password(password)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def valid_configuration(configuration):
    flat_validation_params = [item for sublist in inputparams.params.values() for item in sublist]
    validation_errors = {}
    valid = True
    for param in flat_validation_params:
        key = param[2]
        expected = param[5]
        required = param[4]
        if not (key in configuration):
            if isinstance(expected[0], bool):
                configuration[key] = False  # default value for booleans is false
            else:
                valid = False
                validation_errors[key] = 'Key is not in configuration!'
            continue
        value = configuration[key]
        if required is None and not value:
            configuration[key] = None
            continue
        if isinstance(expected, list):
            if isinstance(expected[0], str):
                if not (value in expected):
                    valid = False
                    validation_errors[key] = 'Selected value is not in the list of valid values!'
                    continue
            elif isinstance(expected[0], bool):
                if value.lower() == 'true':
                    configuration[key] = True
                elif value.lower() == 'false':
                    configuration[key] = False
                else:
                    valid = False
                    validation_errors[key] = 'Boolean must be true or false!'
                    continue
            elif isinstance(expected[0], float):
                try:
                    configuration[key] = float(value)
                    if float(value) > expected[1] or float(value) < expected[0]:
                        raise ValueError()
                except ValueError:
                    valid = False
                    validation_errors[key] = f'Value is not in range from {expected[0]} to {expected[1]}!'
                    continue
            elif isinstance(expected[0], int):
                try:
                    configuration[key] = int(float(value))
                    if int(float(value)) > expected[1] or int(float(value)) < expected[0]:
                        raise ValueError()
                except ValueError:
                    valid = False
                    validation_errors[key] = f'Value is not in range from {expected[0]} to {expected[1]}!'
                    continue
        elif isinstance(expected, str):
            if not (re.match(expected, value)):
                valid = False
                validation_errors[key] = 'Invalid input string!'
                continue
    return [valid, validation_errors]


@app.route('/')
@app.route('/index')
def index():
    if not logged_in():
        return redirect('/login')
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if valid_login(request.form['username'], request.form['password']):
            return log_the_user_in(request.form['username'])
        else:
            error = 'Invalid username/password'

    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/index')


@app.route('/overview')
def overview():
    if not logged_in():
        return redirect('/login')

    current_user = get_current_user()

    active_config_runs = ConfigurationRun.query.filter(and_(ConfigurationRun.executor_id == current_user.id, and_(
        ConfigurationRun.finished_date == None, ConfigurationRun.failed_date == None))).all()

    config_runs = ConfigurationRun.query.filter(and_(ConfigurationRun.executor_id == current_user.id, or_(
        ConfigurationRun.finished_date != None, ConfigurationRun.failed_date != None))).order_by(
        desc(ConfigurationRun.started_date), desc(ConfigurationRun.finished_date), desc(ConfigurationRun.failed_date)).all()

    return render_template('overview.html', active_config_runs=active_config_runs, config_runs=config_runs)


@app.route('/status')
@app.route('/status/<int:config_run_id>')
def status(config_run_id=None):
    if not logged_in():
        return redirect('/login')

    if config_run_id is None:
        current_user = get_current_user()
        config_run = ConfigurationRun.query.filter_by(executor_id=current_user.id).order_by(desc(ConfigurationRun.started_date)).first()
    else:
        config_run = ConfigurationRun.query.filter_by(id=config_run_id).first()

    return render_template('status.html', config_run=config_run)


@app.route('/status/stream/log/<int:config_run_id>')
def log_stream(config_run_id):
    if not logged_in():
        return redirect('/login')

    def generate():
        db_session = Session()
        config_run = db_session.query(ConfigurationRun).filter_by(id=config_run_id).first()
        scenario_id = config_run.configuration.scenario_id
        Session.remove()
        path = os.path.join(get_data_path(scenario_id, config_run_id), LOG_FILENAME)

        while not os.path.isfile(path):
            sleep(0.1)

        with open(path, 'rb', 1) as f:
            while True:
                yield f.read()
                sleep(0.1)

    return app.response_class(generate(), mimetype='text/plain')


@app.route('/status/stream/result/<int:config_run_id>')
def result_stream(config_run_id):
    if not logged_in():
        return redirect('/login')

    def generate():
        db_session = Session()
        config_run = db_session.query(ConfigurationRun).filter_by(id=config_run_id).first()
        scenario_id = config_run.configuration.scenario_id
        Session.remove()
        path = os.path.join(get_data_path(scenario_id, config_run_id), RESULT_FILENAME)

        while not os.path.isfile(path):
            sleep(0.1)

        with open(path, 'rb', 1) as f:
            while True:
                yield f.read()
                sleep(0.1)

    return app.response_class(generate(), mimetype='text/plain')


@app.route('/configure', methods=['GET', 'POST'])
def configure():
    if not logged_in():
        return redirect('/login')

    last_configuration = None
    last_run_for_configuration = None
    validation = [None, None]

    if request.method == 'POST':
        configuration = Configuration(creator_id=get_current_user().id)

        uploaded_configuration = dict(request.form)

        validation = valid_configuration(uploaded_configuration)

        if not validation[0]:
            flash(f'Invalid form data: {validation[1]}', 'error')
        else:
            scenario_id = str(uuid.uuid4())
            uploaded_configuration['scenario_id'] = scenario_id
            configuration.scenario_id = scenario_id
            configuration.configuration = json.dumps(uploaded_configuration)
            last_configuration = uploaded_configuration
            file_paths = []
            files = request.files.getlist('file')
            if files is None or len(files) == 0:
                flash('No files provided', 'error')
            else:
                for file in files:
                    if file.filename == '':
                        flash('File with empty name found', 'error')
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        path = os.path.join(UPLOAD_FOLDER, filename)
                        file.save(path)
                        file_paths.append(path)
                configuration.files = json.dumps(file_paths)
                flash('Uploaded files', 'success')

            db.session.add(configuration)
            db.session.commit()
            flash('Saved configuration', 'success')
    else:
        last_config_item = Configuration.query.filter_by(creator_id=get_current_user().id).order_by(
            desc(Configuration.created_date)).first()
        if last_config_item is not None:
            last_run_for_configuration = ConfigurationRun.query.filter_by(configuration_id=last_config_item.id).first()
            last_configuration = json.loads(last_config_item.configuration)

    return render_template('configure.html', last_configuration=last_configuration,
                           last_run_for_configuration=last_run_for_configuration, validation_errors=validation[1])


@app.route('/configure/run', methods=['GET'])
def run_configuration():
    if not logged_in():
        return redirect('/login')

    current_user = get_current_user()
    last_config_item = Configuration.query.filter_by(creator_id=current_user.id).order_by(desc(Configuration.created_date)).first()
    scenario_id = None
    config_run_id = None

    if last_config_item is not None:
        scenario_id = last_config_item.scenario_id
        filename = os.path.join(CONFIG_FOLDER, str(current_user.id), datetime.today().strftime('%Y-%m-%d-%H-%M-%S-%f') + '_config_run.json')
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        config_run = ConfigurationRun()
        config_run.configuration_id = last_config_item.id
        config_run.executor_id = current_user.id
        config_run.configuration_file_path = filename
        config_run.status = 'STARTED'

        db.session.add(config_run)
        db.session.commit()
        config_run_id = config_run.id

        config = json.loads(last_config_item.configuration)
        config['config_run_id'] = config_run_id
        config['data_path'] = get_data_path(scenario_id, config_run_id)

        with open(filename, "w") as f:
            f.write(json.dumps(config))

        os.makedirs(get_data_path(scenario_id, config_run_id), exist_ok=True)

        args = [TCAT_PYTHON_EXE, TCAT_RUN_FILE, filename]
        popen_and_call(finished_config_run, failed_config_run, config_run.id, TCAT_DIR, args)

    response = dict()
    response['scenario_id'] = scenario_id
    response['config_run_id'] = config_run_id

    return response


@app.route('/configure/run/plot/<string:scenario_id>/<int:config_run_id>', methods=['GET'])
def get_plot_images(scenario_id='', config_run_id=-1):
    if not logged_in():
        return redirect('/login')

    config_run = ConfigurationRun.query.filter_by(id=config_run_id).first()
    response = dict()
    response['scenario_id'] = scenario_id
    response['config_run_id'] = config_run_id
    plot_files = []
    failed = config_run.failed_date is not None
    finished = config_run.finished_date is not None

    path = get_data_path(scenario_id, config_run_id)

    for f in PLOT_IMAGE_NAMES:
            if os.path.isfile(os.path.join(path, f)):
                plot_files.append(f)

    response['plot_files'] = plot_files
    response['failed'] = failed
    response['finished'] = finished

    return response


@app.route('/configure/run/plot/<string:scenario_id>/<int:config_run_id>/<string:filename>', methods=['GET'])
def get_plot_image(scenario_id, config_run_id=-1, filename=''):
    if not logged_in():
        return redirect('/login')

    filename = os.path.join(get_data_path(scenario_id, config_run_id), filename)
    loading_time = 0
    while os.stat(filename).st_size == 0 and loading_time < MAX_FILE_LOAD_DURATION_IN_SEC:
        loading_time += 0.1
        sleep(0.1)

    with open(filename, "r+b") as f:
        image_binary = f.read()

        response = make_response(base64.b64encode(image_binary))
        response.headers.set('Content-Type', mimetypes.types_map[os.path.splitext(filename)[1]])
        response.headers.set('Content-Disposition', 'attachment', filename=os.path.basename(filename))
        return response


@app.route('/download/run/<string:scenario_id>/<int:config_run_id>', methods=['GET'])
def download_run_data(scenario_id, config_run_id):
    if not logged_in():
        return redirect('/login')

    config = Configuration.query.filter_by(scenario_id=scenario_id).first()
    config_run = ConfigurationRun.query.filter_by(id=config_run_id).first()

    if config is None or config_run is None:
        return 'No configuration run found with the provided scenario_id and config_run_id'

    files_path = get_data_path(scenario_id, config_run_id)
    files = os.listdir(files_path)
    file_obj = io.BytesIO()

    with zipfile.ZipFile(file_obj, 'w') as zip_file:
        for f in files:
            filename = os.path.basename(f)
            data = zipfile.ZipInfo(filename)
            data.date_time = time.localtime(time.time())[:6]
            data.compress_type = zipfile.ZIP_DEFLATED
            file_data = open(os.path.join(files_path, filename), 'rb')
            zip_file.writestr(data, file_data.read())
            file_data.close()

    file_obj.seek(0)
    return send_file(file_obj, attachment_filename=f'{scenario_id}.zip', as_attachment=True)


app.jinja_env.globals.update(logged_in=logged_in, inputparams=inputparams.params)

if __name__ == '__main__':
    app.run()