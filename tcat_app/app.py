import base64
import io
import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
import time
import uuid
import zipfile
from datetime import datetime
from operator import and_, or_
from time import sleep

from astropy.time import Time
from dotenv import load_dotenv
from flask import Flask, request, render_template, flash, make_response, send_file, redirect, url_for, jsonify
from flask_oidc import OpenIDConnect
from sqlalchemy import desc
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from tcat_app import inputparams
from ACT_Space_Debris_Index.sdi_run_code import sdi_main
from ACT_atmospheric_emissions.atm_run_code import atm_main
from tcat_app.models import db, Configuration, ConfigurationRun
from ScenarioDatabase.ScenariosSetupFromACT.ScenarioADRSetupFromACT import ScenarioADRSetupFromACT
from logging.config import dictConfig
from astropy import units as astro_units

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

load_dotenv()  # sets values from .env file as environment vars, *.env files are ignored when creating the docker
# image. so the values for the docker image come from the dockerfile and the provided arguments

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
        'OIDC_CLIENT_SECRETS': os.getenv('CLIENT_SECRETS_FILE'),
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


def valid_configuration(configuration, params):
    flat_validation_params = [item for sublist in params.values() for item in sublist]
    validation_errors = {}
    valid = True
    kickstage_use_database = False
    launcher_use_database = False

    for param in flat_validation_params:
        type = param[1]
        key = param[2]
        expected = param[5]
        required = param[4]

        if key == 'kickstage_use_database':
            kickstage_use_database = key in configuration and configuration['kickstage_use_database'] == 'on'
        elif key == 'launcher_use_database':
            launcher_use_database = key in configuration and configuration['launcher_use_database'] == 'on'

        if launcher_use_database and key in ['launcher_performance', 'launcher_fairing_diameter',
                                             'launcher_fairing_cylinder_height', 'launcher_fairing_total_height',
                                             'launcher_perf_interpolation_method']:
            continue

        if kickstage_use_database and key in ['kickstage_height', 'kickstage_diameter', 'kickstage_initial_fuel_mass',
                                              'kickstage_prop_thrust', 'kickstage_prop_isp',
                                              'kickstage_propulsion_dry_mass', 'kickstage_dispenser_dry_mass',
                                              'kickstage_struct_mass', 'kickstage_propulsion_type']:
            continue

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
        if type == 'datetime-local':
            # TODO: add date parsing and validation
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


def get_status(config_run_id):
    db_session = Session()
    config_run = db_session.query(ConfigurationRun).filter_by(id=config_run_id).first()
    Session.remove()
    if config_run.status == 'FAILED':
        return False
    elif config_run.status == 'FINISHED':
        return False

    return True


def generate(config_run_id, file):
    db_session = Session()
    config_run = db_session.query(ConfigurationRun).filter_by(id=config_run_id).first()
    scenario_id = config_run.configuration.scenario_id
    Session.remove()
    path = os.path.join(get_data_path(scenario_id, config_run_id), file)

    in_progress = True

    while not os.path.isfile(path):
        sleep(0.1)

    with open(path, 'rb', 1) as f:
        count = 0
        while in_progress:
            yield f.read()
            sleep(0.1)
            count = count + 1
            if count == 30:
                count = 0
                in_progress = get_status(config_run_id)
                if not in_progress:
                    yield f.read()


@app.route('/status/stream/log/<int:config_run_id>')
@oidc.require_login
def log_stream(config_run_id):
    return app.response_class(generate(config_run_id, LOG_FILENAME), mimetype='text/plain')


@app.route('/status/stream/result/<int:config_run_id>')
@oidc.require_login
def result_stream(config_run_id):
    return app.response_class(generate(config_run_id, RESULT_FILENAME), mimetype='text/plain')


def configure(current_scenario, template, params):
    current_user_email = get_user_info()
    last_configuration = None
    last_run_for_configuration = None
    validation = [None, None]
    is_reset = False

    if request.method == 'POST':
        uploaded_configuration = dict(request.form)
        validation = valid_configuration(uploaded_configuration, params)

        uploaded_configuration['scenario'] = current_scenario

        if not validation[0]:
            flash(f'Invalid form data: {validation[1]}', 'error')
            last_configuration = uploaded_configuration
        else:
            last_configuration = store_configuration(uploaded_configuration, current_user_email)
            flash('Saved configuration', 'success')
    else:
        reset_values = request.args.get('reset')
        if reset_values != 'true':
            last_config_item = Configuration.query.filter(and_(Configuration.creator_email == current_user_email,
                                                               Configuration.scenario == current_scenario)).order_by(
                desc(Configuration.created_date)).first()
            if last_config_item is not None:
                last_run_for_configuration = ConfigurationRun.query.filter_by(
                    configuration_id=last_config_item.id).first()
                last_configuration = json.loads(last_config_item.configuration)
        else:
            is_reset = True

    return render_template(template, last_configuration=last_configuration,
                           last_run_for_configuration=last_run_for_configuration, validation_errors=validation[1],
                           is_reset=is_reset)


@app.route('/configure-adr', methods=['GET', 'POST'])
@oidc.require_login
def configure_adr():
    return configure('adr', 'configure_adr.html', inputparams.adr_mission_params)


@app.route('/configure-constellation-deployment', methods=['GET', 'POST'])
@oidc.require_login
def configure_constellation_deployment():
    return configure('constellation_deployment', 'configure_constellation_deployment.html',
                     inputparams.constellation_mission_params)


def store_configuration(conf, current_user_email):
    configuration = Configuration(creator_email=current_user_email)
    configuration.scenario_id = str(uuid.uuid4())
    configuration.scenario = conf['scenario']
    configuration.scenario_name = conf['constellation_name']
    configuration.configuration = json.dumps(conf)
    db.session.add(configuration)
    db.session.commit()
    return conf


@app.route('/get-config-names', methods=['POST'])
@oidc.require_login
def get_config_names():
    if 'file' not in request.files:
        flash('No file part')
        return make_response(jsonify({'error': 'No file part'}), 400)

    file, action = validate_and_get_file()

    if file is not None:
        file.seek(0)
        file_content = file.stream.read()

        # Create linker object and select ACT configuration
        a2t = ScenarioADRSetupFromACT()
        try:
            a2t.open_act_config_json(file_content.decode('utf-8'))
            config_names = a2t.get_all_configs_name()
            return make_response(jsonify({'config_names': config_names}), 200)
        except Exception as e:
            flash(f'Error parsing ACT file: {e}', 'error')
            return make_response(jsonify({'error': f'Error parsing ACT file: {e}'}), 400)

    return make_response(jsonify({'error': 'No file'}), 400)


@app.route('/configure-from-file', methods=['POST'])
@oidc.require_login
def configure_from_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file_type = request.args.get('type')

    if file_type == 'act':
        return handle_configure_for_act_file()

    return handle_configure_for_tcat_file()


def handle_configure_for_act_file():
    scenario = 'adr'
    current_user_email = get_user_info()
    config_name = request.form['act-config-name']

    if config_name is None:
        flash('No configuration name provided')
        return redirect(url_for('configure_adr'))

    file, action = validate_and_get_file()

    if file is not None:
        file.seek(0)
        file_content = file.stream.read()

        # Create linker object and select ACT configuration
        a2t = ScenarioADRSetupFromACT()
        try:
            a2t.open_act_config_json(file_content.decode('utf-8'))
            # Read configuration
            a2t.read_act_config(config_name)

            # If no engines in the childrenblocks, here is the solution:
            engines_name = a2t.get_all_engines_name(config_name)
            a2t.read_kickstage_engine_parameters(config_name, engines_name[0])
            a2t.read_servicer_engine_parameters(config_name, engines_name[0])

            # Export reading to tcat input .json
            conf = a2t.get_config_as_tcat_json()
            store_configuration(json.loads(conf), current_user_email)
        except Exception as e:
            flash(f'Error parsing ACT file: {e}', 'error')
            return redirect(url_for('configure_adr'))
    else:
        if action is not None:
            return action

    if scenario == 'adr':
        highlight_params = [
            'mission_architecture',
            'verbose',
            'tradeoff_mission_price_vs_duration',
            'constellation_name',
            'sat_mass',
            'sat_volume',
            'n_planes',
            'n_sats_per_plane',
            'plane_distribution_angle',
            'sats_reliability',
            'seed_random_sats_failure',
            'launcher_performance',
            'launcher_perf_interpolation_method',
            'kickstage_remaining_fuel_margin',
            'apogee_sats_disposal',
            'perigee_sats_disposal',
            'inc_sats_disposal'
        ]

        last_config_item = Configuration.query.filter(and_(Configuration.creator_email == current_user_email,
                                                           Configuration.scenario == scenario)).order_by(
            desc(Configuration.created_date)).first()
        if last_config_item is not None:
            last_run_for_configuration = ConfigurationRun.query.filter_by(configuration_id=last_config_item.id).first()
            last_configuration = json.loads(last_config_item.configuration)

        request.url.replace('configure-from-file', 'configure-adr')

        return render_template('configure_adr.html', last_configuration=last_configuration,
                               last_run_for_configuration=last_run_for_configuration, validation_errors=[],
                               highlight_params=highlight_params)


def handle_configure_for_tcat_file():
    scenario = 'constellation_deployment'
    current_user_email = get_user_info()
    file, action = validate_and_get_file()

    if file is not None:
        file.seek(0)
        file_content = file.stream.read()
        uploaded_config = json.loads(file_content.decode('utf-8'))

        try:
            if uploaded_config['scenario'] is None:
                flash('No scenario specified', 'error')
                return redirect(request.url)

            scenario = uploaded_config['scenario']
            valid = valid_configuration(uploaded_config,
                                        inputparams.adr_mission_params) if scenario == 'adr' else valid_configuration(
                uploaded_config, inputparams.constellation_mission_params)

            if valid[0]:
                store_configuration(uploaded_config, current_user_email)
            else:
                msg = ''
                for k, v in valid[1].items():
                    msg += f'\n{k}: {v}'
                flash(f'Invalid configuration{msg}', 'error')
        except Exception as e:
            flash(f'Invalid configuration: {e}', 'error')
            return redirect(request.url)
    else:
        if action is not None:
            return action

    return redirect(url_for('configure_adr') if scenario == 'adr' else url_for('configure_constellation_deployment'))


def validate_and_get_file():
    file = request.files['file']
    if file is None:
        flash('File error', 'error')
        return None, None
    if file.filename == '':
        flash('File has empty name', 'error')
        return None, redirect(request.url)
    if file and allowed_file(file.filename):
        return file, None
    else:
        flash('File not supported', 'error')
        return None, None


def run_configuration(conf_scenario):
    current_user_email = get_user_info()
    last_config_item = Configuration.query.filter(
        and_(Configuration.creator_email == current_user_email, Configuration.scenario == conf_scenario)).order_by(
        desc(Configuration.created_date)).first()
    scenario_id = None
    config_run_id = None

    if last_config_item is not None:
        scenario_id = last_config_item.scenario_id
        scenario = last_config_item.scenario
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
        config['dir_path_for_output_files'] = get_data_path(scenario_id, config_run_id)

        with open(filename, "w") as f:
            f.write(json.dumps(config))

        os.makedirs(get_data_path(scenario_id, config_run_id), exist_ok=True)

        args = [TCAT_PYTHON_EXE, TCAT_RUN_FILE, filename]
        popen_and_call(finished_config_run, failed_config_run, config_run.id, TCAT_DIR, args)

    response = dict()
    response['scenario_id'] = scenario_id
    response['config_run_id'] = config_run_id

    return response


@app.route('/configure/run/adr', methods=['GET'])
@oidc.require_login
def run_adr():
    return run_configuration('adr')


@app.route('/configure/run/constellation-deployment', methods=['GET'])
@oidc.require_login
def run_constellation_deployment():
    return run_configuration('constellation_deployment')


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

    f = open(os.path.join(files_path, f'{scenario_id}-configuration.json'), "w")
    f.write(config.configuration)
    f.close()

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
    return send_file(file_obj, download_name=f'{scenario_id}.zip', as_attachment=True)


@app.route('/api/v1/calculations/sdi', methods=['POST'])
@oidc.accept_token(require_token=True)
def get_sdi():
    data = request.get_json()

    if data is None:
        return '{"error": "No data provided"}'

    result = sdi_main(Time(data['startingEpoch'], scale="tdb"),
                      data['opDuration'] * astro_units.year if data['opDuration'] is not None else None,
                      data['mass'] * astro_units.kg if data['mass'] is not None else None,
                      data['crossSection'] * astro_units.m ** 2 if data['crossSection'] is not None else None,
                      data['meanThrust'] * astro_units.N if data['meanThrust'] is not None else None,
                      data['isp'] * astro_units.s if data['isp'] is not None else None,
                      data['numberOfLaunches'],
                      data['apogeeObjectOp'] * astro_units.km if data['apogeeObjectOp'] is not None else None,
                      data['perigeeObjectOp'] * astro_units.km if data['perigeeObjectOp'] is not None else None,
                      data['incObjectOp'] * astro_units.deg if data['incObjectOp'] is not None else None,
                      data['eolManoeuvre'],
                      data['pmdSuccess'],
                      data['apogeeObjectDisp'] * astro_units.km if data['apogeeObjectDisp'] is not None else None,
                      data['perigeeObjectDisp'] * astro_units.km if data['perigeeObjectDisp'] is not None else None,
                      data['incObjectDisp'] * astro_units.deg if data['incObjectDisp'] is not None else None,
                      data['adrStage'],
                      data['mAdr'] * astro_units.kg if data['mAdr'] is not None else None,
                      data['adrCrossSection'] * astro_units.m ** 2 if data['adrCrossSection'] is not None else None,
                      data['adrMeanThrust'] * astro_units.N if data['adrMeanThrust'] is not None else None,
                      data['adrIsp'] * astro_units.s if data['adrIsp'] is not None else None,
                      data['adrManoeuvreSuccess'],
                      data['adrCaptureSuccess'],
                      data['mDebris'] * astro_units.kg if data['mDebris'] is not None else None,
                      data['debrisCrossSection'] * astro_units.m ** 2 if data['debrisCrossSection'] is not None else None,
                      data['apogeeDebris'] * astro_units.km if data['apogeeDebris'] is not None else None,
                      data['perigeeDebris'] * astro_units.km if data['perigeeDebris'] is not None else None,
                      data['incDebris'] * astro_units.deg if data['incDebris'] is not None else None,
                      data['apogeeDebrisRemoval'] * astro_units.km if data['apogeeDebrisRemoval'] is not None else None,
                      data['perigeeDebrisRemoval'] * astro_units.km if data['perigeeDebrisRemoval'] is not None else None,
                      data['incDebrisRemoval'] * astro_units.deg if data['incDebrisRemoval'] is not None else None,
                      os.path.join(TCAT_DIR, 'ACT_Space_Debris_Index/sdi_space_debris_CF_for_code.csv'),
                      os.path.join(TCAT_DIR, 'ACT_Space_Debris_Index/sdi_reduced_lifetime.csv'))

    response = {'LCS3': result['LCS3'].value, 'LCS4': result['LCS4'].value}
    return jsonify(response)


@app.route('/api/v1/calculations/atm', methods=['POST'])
@oidc.accept_token(require_token=True)
def get_atm():
    data = request.get_json()

    if data is None:
        return '{"error": "No data provided"}'

    result = atm_main(TCAT_DIR,
                      data['launcher'],
                      data['engine'],
                      data['numberOfEngines'],
                      data['propType'],
                      data['isp'] * astro_units.s if data['isp'] is not None else None,
                      data['ignitionTimestamp'] * astro_units.s if data['ignitionTimestamp'] is not None else None,
                      data['cutoffTimestamp'] * astro_units.s if data['cutoffTimestamp'] is not None else None,
                      data['numberOfLaunches'],
                      data['rawTrajectory'],
                      data['rawThrustCurve'],
                      plotting=False)

    return jsonify(result)


app.jinja_env.globals.update(inputparams=inputparams)

if __name__ == '__main__':
    app.run()
    app.logger.info('Starting application')
