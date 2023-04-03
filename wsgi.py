import os

from tcat_app.app import app as application

HOST = os.getenv('HOST')
PORT = os.getenv('PORT')

if __name__ == "__main__":
    application.run(host=HOST, port=PORT)
