#!/bin/bash

/usr/local/bin/python /app/tcat-app/create_client_secrets_from_env.py /app/tcat-app/client_secrets.json
/usr/bin/systemctl enable --now tcat-app.service;