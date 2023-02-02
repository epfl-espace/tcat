#!/bin/bash

/usr/local/bin/python /app/tcat_app/create_client_secrets_from_env.py /app/tcat_app/client_secrets.json
/usr/bin/systemctl enable --now tcat-app.service;