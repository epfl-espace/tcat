import os
import sys
import json
from dotenv import load_dotenv

if len(sys.argv) > 2:
    env_file = sys.argv[2]
    load_dotenv(env_file)

web_data = {'issuer': os.getenv('IDP_ISSUER'), 'auth_uri': os.getenv('IDP_AUTH_URI'),
            'client_id': os.getenv('IDP_CLIENT_ID'), 'client_secret': os.getenv('IDP_CLIENT_SECRET'),
            'redirect_uris': [os.getenv('IDP_REDIRECT_URI')], 'userinfo_uri': os.getenv('IDP_USERINFO_URI'),
            'token_uri': os.getenv('IDP_TOKEN_URI'), 'token_introspection_uri': os.getenv('IDP_INTROSPECTION_URI')}

data = {'web': web_data}
json_data = json.dumps(data)

f = open(sys.argv[1], "w")
f.write(json_data)
f.close()
