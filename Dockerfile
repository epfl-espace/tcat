FROM python:3.9.15

ENV BASE_FOLDER=/tcat-app-data
ENV TCAT_DIR=/app
ENV TCAT_PYTHON_EXE=/usr/local/bin/python
ENV TCAT_RUN_FILE=RunTCAT.py
ENV DATABASE_URI=sqlite:////tcat-app-db/tcat.db
ENV CLIENT_SECRETS_FILE=./tcat_app/client_secrets.json
ENV HOST=0.0.0.0
ENV PORT=5000
ENV ALLOWED_EXTENSIONS=json
ENV PLOT_IMAGE_NAMES=2D_plotRAAN_altitude.png,2D_plotRAAN_anomaly.png,3D_plot.png,InterpolationGraph.gif
ENV LOG_FILENAME=log.txt
ENV RESULT_FILENAME=result.txt
ENV MAX_FILE_LOAD_DURATION_IN_SEC=30

RUN apt update && apt-get install systemctl -y && apt install nginx -y
RUN rm /etc/nginx/sites-enabled/default && rm /etc/nginx/sites-available/default

WORKDIR /app
COPY ./requirements.txt ./requirements.txt
RUN pip install -U uwsgi
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
WORKDIR /app/tcat_app

COPY ./ScenarioDatabase ./ScenarioDatabase

RUN chmod 777 ./startup.sh
RUN mv ./tcat-app /etc/nginx/sites-available/
RUN ln -s /etc/nginx/sites-available/tcat-app /etc/nginx/sites-enabled

RUN mv ./tcat-app.service /etc/systemd/system/tcat-app.service
RUN systemctl daemon-reload
RUN systemctl reload nginx

STOPSIGNAL SIGQUIT

CMD /app/tcat_app/startup.sh && nginx -g 'daemon off;'