# TCAT

 ## TCAT - Project setup

 ### Python requirements
   - Install the required python packages from `requirements.txt`

 ### Configure paths and directories
   - Create the folder 'Results' in the root directory

 ### Run the app
   - To start the tool run `Run_Constellation.py` and add as parameters the path that links to the `Constellation_new_v1.json` file
   - Change verbose in `Constellation_new_v1.json` to true, if you want to output plot images

 ## TCAT-APP Project setup

 ### Requirements:
   - [NodeJS](https://nodejs.org/) (_v14 or higher is required for tailwindcss_)
   - [npm](https://www.npmjs.com/)
   - [tailwindcss](https://tailwindcss.com/)
     - Install with npm -> `npm install tailwindcss`

 > The following package installations can be skipped when installing the packages from the requirements.txt
   - [Flask](https://flask.palletsprojects.com/en/2.0.x/)
     - Install with pip -> `pip install Flask`
   - [SQLAlchemy](https://www.sqlalchemy.org)
     - Install with pip -> `pip install SQLAlchemy`
   - [Flask SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/en/2.x/)
     - Install with pip -> `pip install Flask-SQLAlchemy`
   - [python-dotenv](https://pypi.org/project/python-dotenv/)
     - Install with pip -> `pip install python-dotenv`
   - [flask-oidc](https://pypi.org/project/flask-oidc/)
     - Install with pip -> `pip install flask-oidc`

 ### Setup:
 #### Python requirements
   - Install the required python packages from `requirements.txt`

 #### NPM
   - Run `npm install` **inside the static directory**
   - Still inside the static directory run `npm run 'buildcss'` to create the css/main.css (**Needs to run before every build, when the template html files changed.**)

 #### Configure paths and directories
   - Copy `.env.example` to `.env`
   - Adjust Variables to your needs:
     - Change `BASE_FOLDER` to an accessible (read and write) directory where the data can be stored
     - Change `TCAT_DIR` to the directory where you tcat repository is stored
     - Change `TCAT_PYTHON_EXE` to the path to your python executable (e.g. virtual environment) where all the needed packages are installed to run tcat
     - Change `DATABASE_URI` to an accessible (read and write) directory where you want to store the database file for the tcat-app
     - Change `APP_SECRET` to a newly generated secret with `python -c "import uuid; print(uuid.uuid4().hex+uuid.uuid4().hex)"`
     - Change `SECRET_KEY` to a newly generated secret with `python -c "import uuid; print(uuid.uuid4().hex+uuid.uuid4().hex)"`
   - Create the following subfolders inside the `BASE_FOLDER` path: `uploads`, `configs` and `tcat-data`

 #### Run the app
   - To start the app run `app.py`


 ## Deployment ⬆️

To deploy the app pull the container from [https://github.com/epfl-espace/tcat/pkgs/container/tcat](https://github.com/epfl-espace/tcat/pkgs/container/tcat).

### Docker Compose Example

> Replace all items in `<>` with your own values.

```dockerfile
version: '2'
services:
    tcat-app:
        image: ghcr.io/epfl-espace/tcat:main
        container_name: tcat
        ports:
            - <your-port>:80
        restart: always
        environment:
            IDP_ISSUER: <idp-issuer>
            IDP_AUTH_URI: <idp-auth-uri>
            IDP_CLIENT_ID: <idp-client-id>
            IDP_CLIENT_SECRET: <idp-client-secret>
            IDP_REDIRECT_URI: <idp-redirect-uri>
            IDP_USERINFO_URI: <idp-userinfo-uri>
            IDP_TOKEN_URI: <idp-token-uri>
            IDP_INTROSPECTION_URI: <idp-introspection-uri>
            APP_SECRET: <generate-random-secret>
            SECRET_KEY: <generate-random-secret>
        volumes:
            -   <custom-path>/docker-data-out:/tcat-app-data
            -   <custom-path>/docker-data-db:/tcat-app-db
```