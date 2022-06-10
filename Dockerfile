FROM python:3.9.12

ARG idp_issuer
ARG idp_auth_uri
ARG idp_client_id
ARG idp_client_secret
ARG idp_redirect_uri
ARG idp_userinfo_uri
ARG idp_token_uri
ARG idp_introspection_uri
ARG app_secret
ARG secret_key

ENV IDP_ISSUER=${idp_issuer}
ENV IDP_AUTH_URI=${idp_auth_uri}
ENV IDP_CLIENT_ID=${idp_client_id}
ENV IDP_CLIENT_SECRET=${idp_client_secret}
ENV IDP_REDIRECT_URI=${idp_redirect_uri}
ENV IDP_USERINFO_URI=${idp_userinfo_uri}
ENV IDP_TOKEN_URI=${idp_token_uri}
ENV IDP_INTROSPECTION_URI=${idp_introspection_uri}

ENV BASE_FOLDER=/tcat-app-data
ENV TCAT_DIR=/app
ENV TCAT_PYTHON_EXE=/bin/python
ENV TCAT_RUN_FILE=Run_Constellation.py
ENV DATABASE_URI=sqlite:////tcat-app-db/tcat.db
ENV APP_SECRET=${app_secret}
ENV HOST=0.0.0.0
ENV PORT=5000
ENV ALLOWED_EXTENSIONS=txt
ENV PLOT_IMAGE_NAMES=2D_plotRAAN_altitude.png,2D_plotRAAN_anomaly.png,3D_plot.png,InterpolationGraph.gif
ENV LOG_FILENAME=log.txt
ENV RESULT_FILENAME=result.txt
ENV MAX_FILE_LOAD_DURATION_IN_SEC=30
ENV SECRET_KEY=${secret_key}

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt
RUN pip install uwsgi

WORKDIR /app/tcat-app

RUN python create_client_secrets_from_env.py ./client_secrets.json

CMD [ "python", "app.py" ]