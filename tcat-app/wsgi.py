import os
from app import app as application
from dotenv import load_dotenv

load_dotenv()  # sets values from .env file as environment vars

HOST = os.getenv('HOST')
PORT = os.getenv('PORT')

if __name__ == "__main__":
    application.run(host=HOST, port=PORT)