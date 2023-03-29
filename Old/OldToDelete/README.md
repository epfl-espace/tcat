# TCAT

## TCAT - Project setup

### Python requirements
  - Install the required python packages from `requirements.txt`

### Configure paths and directories
  - Create the folder 'Results' in the root directory
  - Opent the `test_config.json` file in the root directory and modify the last item '# data_path' to match the path of the folder 'Results' you just created

### Run the app
  - To start the tool run `test_from_file.py` and add as parameters the path that links to the 'test_config.json' file
  - Manually change the other relevant parameters in the 'Scenario_ConstellationDeployment.py'
  - Toggle the parameter '#override' in the `test_from_file.py`file to show the log directly in the command line
  
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
  - Create the following subfolders inside the `BASE_FOLDER` path: `uploads`, `configs` and `tcat-data`

#### Add new users
  - Open the `add_user.py` and enter the desired credentials (`add_user('username', 'password', 'email@address.com')`)
  - Run the file `add_user.py` and the user will be created

#### Run the app
  - To start the app run `app.py`


## Deployment ⬆️

### Creating a docker container (_Ubuntu_) 

> This is not necessary if you already have a docker container!

If you don't have docker installed please follow the [instructions on how to install docker](https://docs.docker.com/get-docker/).
To create a docker container with Ubuntu (here version 20.04) run the following command in your terminal _(docker needs to run in the background, otherwise docker commands won't work)_.


```shell
docker run --cap-add=NET_ADMIN -it --entrypoint "/bin/bash" ubuntu:20.04
```

`run` is used to run a container. _By default if the build is not found, docker will build the image. If the image is not found, docker will pull it and build the container. Then it will run the created container_.

`--cap-add` can add certain linux capabilities which won't work by default. In this case we need the `NET_ADMIN` capability to access the iptables which are used by the firewall which we setup later.

`-it` makes the container start look like a terminal connection session. `-i` / `--interactive` flag adds a stdin stream (for input) and the `-t` / `--tty` flag adds a terminal driver.

`--entrypoint` is used to overwrite the default entrypoint of the image. 

---

> This deployment guide is for Ubuntu 20.04

> Based on [Serve Flask with uWSGI](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-uwsgi-and-nginx-on-ubuntu-20-04), [Install Nginx on Ubuntu](https://www.digitalocean.com/community/tutorials/how-to-install-nginx-on-ubuntu-20-04)

#### Setup new user as sudo

First install iptables (_used by the firewall_) and sudo to create users with sudo permissions.

📦 iptables, sudo, systemctl, curl and nano
```shell
apt update
apt-get install iptables sudo systemctl curl nano
```

Next create a new user and add the user to the sudo group.

```shell
adduser docker
adduser docker sudo
```

Now you can switch from the root user to the created user, in this case `docker`.

```shell
su docker
```
> From now on use the created user which is in the sudo group ❗

#### Setup Nginx

1. Installing Nginx

📦 Install nginx.
```shell
sudo apt install nginx
```

2. Adjusting the firewall

> If the ufw command doesn't exist, then you need to install ufw with the following command

📦 Install ufw.
```shell
sudo apt-get install ufw
```

##### Nginx provides three firewall profiles

> port 80 => normal, unencrypted web traffic 🔓

> port 443 => tls/ssl encrypted traffic 🔒

- Nginx Full: opens port 80 and 443
- Nginx HTTP: opens only port 80
- Nginx HTTPS: opens only port 443

Now check if your firewall is active.
```shell
sudo ufw status
```
If not then you need to enable it.
```shell
sudo ufw enable
```
Now apply a desired rule.
```shell
sudo ufw allow 'Nginx HTTPS'
```
You can replace `Nginx HTTPS` with any of the [rules](#nginx-provides-three-firewall-profiles) above for your desired configuration.

#### Setup git

📦 Install git.
```shell
sudo apt-get install git
```
📁 Create a directory for your project (_ie: tcat_).
```shell
sudo mkdir /var/www/tcat
```
Change the ownership of the folder to the docker user and the docker group.
```shell
sudo chown docker:docker tcat-root
```
To access a git repository you need to create an ssh key 🔑.
> The keygenerator will ask you where you want to save the key and if you want to protect it with a passphrase. Make sure your passphrase is empty (_if you want to create an auto deployment process later on, it will be easier without a passphrase_)
```shell
ssh-keygen
```
Now display the generated public key (_change the directory to the one you specified_)
```shell
cat /home/docker/.ssh/id_rsa.pub
```
Now you copy the public key and [add a new deploy key for your repository](https://docs.github.com/en/developers/overview/managing-deploy-keys#deploy-keys).
> In following steps we will clone the repository and setup tcat.

#### Setup Flask with uWSGI

Update apt source list. Needed to install NodeJS (v14) which is required for Tailwindcss.
```
curl -sL https://deb.nodesource.com/setup_14.x | sudo bash -
```
📦 Install all the necessary packages.
```shell
sudo apt install nodejs npm
sudo apt install python3.9 python3-pip python3.9-dev build-essential libssl-dev libffi-dev python3-setuptools python3.9-venv 
```
Create a folder with a virual environment for python (_3.9_).
Clone the repository with ssh.
```shell
git clone git@github.com:epfl-espace/tcat.git
```
Now you have your repository on your server. Change into the directory for the cloned project.
```shell
cd tcat/
```
Create a virtual environment for python. The required modules will be installed in this environment.
> When the virtual environment is created with python3.9 then we can use only the python command when it is active because python will point to python3.9
```shell
python3.9 -m venv venv
```
[Configure the paths and directories for the tcat-app](#configure-paths-and-directories)❗

[Run npm install and build the css](#npm)❗

Now we need to install all the required python modules. To do this, activate the created virtual environment for python.
```shell
source ../venv/bin/activate
```
Now we install the requirements defined in `requirements.txt` for the virtual environment.
```shell
pip install wheel #needed for poliastro - otherwise it could be in the requirements.txt
pip install poliastro #when poliastro is in the requirements file a conflict occures when installing
pip install -r requirements.txt
```
To test if everything worked run the app and check if it starts without any errors.
```shell
python tcat_app/app.py
```
This should generate the following output.
```
 * Serving Flask app 'app' (lazy loading)
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: off
 * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
```

#### Configure uWSGI

Before continuing, you can deactivate the virtual environment.
```shell
deactivate
```
Create a uWSGI configuration file in the project directory.
```shell
nano tcat_app/tcat_app.ini
```
In the file we configrute the following options:

- header, `[uwsgi]` that uWSGI knows to apply the settings
- `module` referring to the created `wsgi.py` file (_without extension_) and the callable within the file `application`
- `master` tells uWSGI to start up in master mode
- `processes` number of processes created to serve requests
- `socket` creates a unix socket (_nginx will pass requests to this socket_)
- `chmod-socket` permissions for the socket
- `vacuum` makes sure to clean up the socket when the process stops
- `die-on-term` helps to ensure that the init system and uWSGI are "aligned"

```ini
[uwsgi]
module = wsgi:application

master = true
processes = 5

socket = tcat-app.sock
chmod-socket = 660
vacuum = true

die-on-term = true
```

#### Creating a system service

> This allows Ubuntu to automatically start/restart uWSGI when the server boots.

```shell
sudo nano /etc/systemd/system/tcat_app.service
```
In the service file we configure the following options:

- start with the section `[Unit]`
- `Description` to describe the service (_is displayed when you call the status of the service_)
- `After` tells the system to only start after the networking target has been reached
- next comes the section `[Service]`
- `User` defines the owner of the process (take the user which has access to all the files configured above❗)
- `Group` defines the group ownership, `www-data` is required that Nginx can communicate with the uWSGI processes
- `WorkingDirectory` directory in which the process "is running"
- `Environment` the environment which is used to run the process (_here we define the path to our python venv_)
- `ExecStart` the executable to start when the service is started
- next comes the section `[Install]`
- `WantedBy` this tells systemd what to link the service to if start at boot is enabled (_in our case the service starts when the regular multi-user system is up and running_)

```ini
[Unit]
Description=uWSGI instance to serve tcat-app
After=network.target

[Service]
User=docker
Group=www-data
WorkingDirectory=/var/www/tcat/tcat-app
Environment="PATH=/var/www/tcat/venv/bin"
ExecStart=/var/www/tcat/venv/bin/uwsgi --ini /var/www/tcat/tcat-app/tcat-app.ini

[Install]
WantedBy=multi-user.target
```
Now start the service and enable it to start at boot. Then you can check the status.
```shell
sudo systemctl start tcat_app.service
sudo systemctl enable tcat_app.service
sudo systemctl status tcat_app.service
```

#### Configure Nginx to proxy requests

Create a nginx configuration file.
```shell
sudo nano /etc/nginx/sites-available/tcat_app
```
In the Nginx configuration file we configure nginx to listen on port 80 and use this block for requests for the project's domain name. The location block matches every request. `include uwsgi_params;` loads some required uWSGI parameters. `uwsgi_pass` tells nginx to pass the request to the socket. **This is the socket we defined in the `tcat-app.ini` file**
```nginx
server {
    listen 80;
    server_name tcat.epfl.ch;

    location / {
        include uwsgi_params;
        uwsgi_pass unix:/var/www/tcat/tcat-app/tcat-app.sock;
    }
}
```
To enable the site we link it from the `nginx/sites-available` to the `nginx/sites-enabled` directory.
```shell
sudo ln -s /etc/nginx/sites-available/tcat_app /etc/nginx/sites-enabled
```
When the file is linked to the `sites-enabled` directory we can test the configurations for syntax errors.
```shell
sudo nginx -t
```
When there are no erros, restart the Nginx process (_to load the new configuration_)
```shell
sudo systemctl restart nginx
```