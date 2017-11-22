import os
import logging
import ConfigParser
from operator import itemgetter
from relativedates import timesince
from datetime import datetime
from flask import Flask, render_template
from boto.s3.connection import S3Connection

# constants
CONFIG_FILENAME = 'app.config'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('s3-backup-dashboard')
logger.info("---------------------------------------------------------------------------")

app = Flask(__name__)

# load config from file, fallback to envvars on production system
settings = ['S3_ACCESS_KEY_ID', 'S3_SECRET_ACCESS_KEY', 'S3_BUCKET', 'APP_BLACKLIST']
try:
    config = ConfigParser.ConfigParser()
    config.read(os.path.join(BASE_DIR, CONFIG_FILENAME))
    for s in settings:
        app.config[s] = config.get('app', s)
except ConfigParser.NoSectionError:
    # if no app.config file then read from environment variables
    for s in settings:
        app.config[s] = os.environ[s]

# get blacklist of apps to ignore (ie. not automated with Backups package
blacklist = set(x.strip() for x in app.config['APP_BLACKLIST'].split(','))

# connect to s3
s3 = S3Connection(app.config['S3_ACCESS_KEY_ID'], app.config['S3_SECRET_ACCESS_KEY'])


@app.route("/")
def index():
    # get everything in the bucket
    bucket = s3.get_bucket(app.config['S3_BUCKET'])
    file_list = [key.name.split('/') for key in sorted(bucket.list())]
    latest_backups = {}
    # build a list of the latest backups per app
    for path_parts in file_list:
        app_name = path_parts[1]
        if app_name in blacklist:
            continue
        date_str = path_parts[2]
        logger.debug(app_name)
        date = datetime.strptime(date_str, '%Y.%m.%d.%H.%M.%S')
        if (app_name not in latest_backups.keys()) or (date > latest_backups[app_name]['date']):
            age = (datetime.now() - date).days
            if age < 1:
                status = 'success'
            elif age < 7:
                status = 'warning'
            else:
                status = 'danger'
            latest_backups[app_name] = {'app_name': app_name,
                                        'date': date,
                                        'relative_date': timesince(date),
                                        'status': status}

    latest_backups = sorted(latest_backups.values(), key=itemgetter('app_name'))
    return render_template("base.html", latest_backups=latest_backups)


if __name__ == "__main__":
    app.debug = True
    app.run()
    logger.info("Started Server")
