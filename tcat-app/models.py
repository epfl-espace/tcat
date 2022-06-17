from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Configuration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    scenario_id = db.Column(db.String(128), nullable=False, unique=True)
    scenario_name = db.Column(db.String(2048), nullable=False)
    creator_email = db.Column(db.String(128), nullable=False)
    configuration = db.Column(db.String(65536), nullable=False)
    created_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    configuration_runs = db.relationship('ConfigurationRun', back_populates='configuration')

    def __repr__(self):
        return '<Configuration %r>' % self.id


class ConfigurationRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    configuration_id = db.Column(db.Integer, db.ForeignKey('configuration.id'), nullable=False)
    executor_email = db.Column(db.String(128), nullable=False)
    configuration_file_path = db.Column(db.String(4096), nullable=False, unique=True)
    started_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    finished_date = db.Column(db.DateTime, nullable=True)
    failed_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(128), nullable=False)
    configuration = db.relationship('Configuration', back_populates='configuration_runs')

    def __repr__(self):
        return '<ConfigurationRun %r>' % self.id
