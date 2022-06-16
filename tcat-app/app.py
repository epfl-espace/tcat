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

from flask import Flask, request, render_template, flash, make_response, send_file, redirect, url_for
from flask_oidc import OpenIDConnect

from werkzeug.utils import secure_filename

import inputparams
from models import db, Configuration, ConfigurationRun
from sqlalchemy import desc
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


def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv('APP_SECRET')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config.update({
        'SECRET_KEY': os.getenv('SECRET_KEY'),
        'TESTING': False,
        'DEBUG': False,
        'OIDC_CLIENT_SECRETS': 'client_secrets.json',
        'OIDC_ID_TOKEN_COOKIE_SECURE': False,
        'OIDC_REQUIRE_VERIFIED_EMAIL': False,
        'OIDC_USER_INFO_ENABLED': True,
        'OIDC_OPENID_REALM': os.getenv('IDP_REALM'),
        'OIDC_SCOPES': ['openid', 'email', 'profile'],
        'OIDC_INTROSPECTION_AUTH_METHOD': 'client_secret_post'
    })
    oidc = OpenIDConnect(app)

    with app.app_context():
        db.init_app(app)
        db.create_all()
        session_factory = sessionmaker(bind=db.engine)
        Session = scoped_session(session_factory)

    return app, Session, oidc


app, Session, oidc = create_app()


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


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_user_info():
    return oidc.user_getinfo(['email'])['email']


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
                configuration[key] = True  # when value is present then true
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
@oidc.require_login
def index():
    return render_template('index.html')


@app.route("/logout")
@oidc.require_login
def logout():
    logout_request = f'{os.getenv("IDP_LOGOUT_URI")}'
    oidc.logout()
    return redirect(logout_request)


@app.route('/overview')
@oidc.require_login
def overview():
    current_user_email = get_user_info()

    active_config_runs = ConfigurationRun.query.filter(and_(ConfigurationRun.executor_email == current_user_email, and_(
        ConfigurationRun.finished_date == None, ConfigurationRun.failed_date == None))).all()

    config_runs = ConfigurationRun.query.filter(and_(ConfigurationRun.executor_email == current_user_email, or_(
        ConfigurationRun.finished_date != None, ConfigurationRun.failed_date != None))).order_by(
        desc(ConfigurationRun.started_date), desc(ConfigurationRun.finished_date),
        desc(ConfigurationRun.failed_date)).all()

    return render_template('overview.html', active_config_runs=active_config_runs, config_runs=config_runs)


@app.route('/status')
@app.route('/status/<int:config_run_id>')
@oidc.require_login
def status(config_run_id=None):
    if config_run_id is None:
        current_user_email = get_user_info()
        config_run = ConfigurationRun.query.filter_by(executor_email=current_user_email).order_by(
            desc(ConfigurationRun.started_date)).first()
    else:
        config_run = ConfigurationRun.query.filter_by(id=config_run_id).first()

    return render_template('status.html', config_run=config_run)


def generate(config_run_id, file):
    db_session = Session()
    config_run = db_session.query(ConfigurationRun).filter_by(id=config_run_id).first()
    scenario_id = config_run.configuration.scenario_id
    Session.remove()
    path = os.path.join(get_data_path(scenario_id, config_run_id), file)

    while not os.path.isfile(path):
        sleep(0.1)

    with open(path, 'rb', 1) as f:
        while True:
            yield f.read()
            sleep(0.1)


@app.route('/status/stream/log/<int:config_run_id>')
@oidc.require_login
def log_stream(config_run_id):
    return app.response_class(generate(config_run_id, LOG_FILENAME), mimetype='text/plain')


@app.route('/status/stream/result/<int:config_run_id>')
@oidc.require_login
def result_stream(config_run_id):
    return app.response_class(generate(config_run_id, RESULT_FILENAME), mimetype='text/plain')


@app.route('/configure', methods=['GET', 'POST'])
@oidc.require_login
def configure():
    current_user_email = get_user_info()
    last_configuration = None
    last_run_for_configuration = None
    validation = [None, None]

    if request.method == 'POST':
        uploaded_configuration = dict(request.form)
        validation = valid_configuration(uploaded_configuration)

        if not validation[0]:
            flash(f'Invalid form data: {validation[1]}', 'error')
        else:
            last_configuration = store_configuration(uploaded_configuration, current_user_email)
            flash('Saved configuration', 'success')
    else:
        last_config_item = Configuration.query.filter_by(creator_email=current_user_email).order_by(
            desc(Configuration.created_date)).first()
        if last_config_item is not None:
            last_run_for_configuration = ConfigurationRun.query.filter_by(configuration_id=last_config_item.id).first()
            last_configuration = json.loads(last_config_item.configuration)

    return render_template('configure.html', last_configuration=last_configuration,
                           last_run_for_configuration=last_run_for_configuration, validation_errors=validation[1])


def store_configuration(conf, current_user_email):
    configuration = Configuration(creator_email=current_user_email)
    scenario_id = str(uuid.uuid4())
    conf['scenario_id'] = scenario_id
    configuration.scenario_id = scenario_id
    configuration.scenario_name = conf['constellation_name']
    configuration.configuration = json.dumps(conf)
    db.session.add(configuration)
    db.session.commit()
    return conf


@app.route('/configure-from-file', methods=['POST'])
@oidc.require_login
def configure_from_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    current_user_email = get_user_info()
    if file is None:
        flash('File error', 'error')
    else:
        if file.filename == '':
            flash('File has empty name', 'error')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            file.seek(0)
            file_content = file.stream.read()
            uploaded_config = json.loads(file_content.decode('utf-8'))
            valid = valid_configuration(uploaded_config)
            if valid[0]:
                store_configuration(uploaded_config, current_user_email)
            else:
                msg = ''
                for k, v in valid[1].items():
                    msg += f'\n{k}: {v}'
                flash(f'Invalid configuration{msg}', 'error')
        else:
            flash('File not supported', 'error')

    return redirect(url_for('configure'))


@app.route('/configure/run', methods=['GET'])
@oidc.require_login
def run_configuration():
    current_user_email = get_user_info()
    last_config_item = Configuration.query.filter_by(creator_email=current_user_email).order_by(
        desc(Configuration.created_date)).first()
    scenario_id = None
    config_run_id = None

    if last_config_item is not None:
        scenario_id = last_config_item.scenario_id
        filename = os.path.join(CONFIG_FOLDER, current_user_email,
                                datetime.today().strftime('%Y-%m-%d-%H-%M-%S-%f') + '_config_run.json')
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        config_run = ConfigurationRun()
        config_run.configuration_id = last_config_item.id
        config_run.executor_email = current_user_email
        config_run.configuration_file_path = filename
        config_run.status = 'STARTED'

        db.session.add(config_run)
        db.session.commit()
        config_run_id = config_run.id

        config = json.loads(last_config_item.configuration)
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
@oidc.require_login
def get_plot_images(scenario_id='', config_run_id=-1):
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
@oidc.require_login
def get_plot_image(scenario_id, config_run_id=-1, filename=''):
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
@oidc.require_login
def download_run_data(scenario_id, config_run_id):
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


app.jinja_env.globals.update(inputparams=inputparams.params)

if __name__ == '__main__':
    app.run()
