import os

from flask import Flask, session
from werkzeug.security import generate_password_hash
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from models import db, User
from dotenv import load_dotenv

load_dotenv()  # sets values from .env file as environment vars


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

        add_user('user11', 'password11', 'email@address11.com')

    return app, Session


app, Session = create_app()
