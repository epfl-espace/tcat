from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    firstname = db.Column(db.String(120), nullable=True)
    lastname = db.Column(db.String(120), nullable=True)
    configurations = db.relationship('Configuration', back_populates='creator')
    configuration_runs = db.relationship('ConfigurationRun', back_populates='executor')

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User %r>' % self.username


class Configuration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    scenario_id = db.Column(db.String(128), nullable=False, unique=True)
    configuration = db.Column(db.String(65536), nullable=False)
    files = db.Column(db.String(65536), nullable=False)
    created_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    creator = db.relationship('User', back_populates='configurations')
    configuration_runs = db.relationship('ConfigurationRun', back_populates='configuration')

    def __repr__(self):
        return '<Configuration %r>' % self.id


class ConfigurationRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    configuration_id = db.Column(db.Integer, db.ForeignKey('configuration.id'), nullable=False)
    executor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    configuration_file_path = db.Column(db.String(4096), nullable=False, unique=True)
    started_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    finished_date = db.Column(db.DateTime, nullable=True)
    failed_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(128), nullable=False)
    configuration = db.relationship('Configuration', back_populates='configuration_runs')
    executor = db.relationship('User', back_populates='configuration_runs')

    def __repr__(self):
        return '<ConfigurationRun %r>' % self.id
