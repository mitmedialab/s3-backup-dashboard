import os, logging, ConfigParser, inflector
from relativedates import timesince
from datetime import datetime
from flask import Flask, render_template, json, jsonify
from boto.s3.connection import S3Connection

# constants
CONFIG_FILENAME = 'app.config'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# setup logging
logging.basicConfig(filename='s3-backup-dashboard.log',level=logging.DEBUG)
log = logging.getLogger('s3-backup-dashboard')
log.info("---------------------------------------------------------------------------")

# read in app config
config = ConfigParser.ConfigParser()
config.read(os.path.join(BASE_DIR,CONFIG_FILENAME))

# connect to s3
s3 = S3Connection(config.get('s3','access_key_id'), config.get('s3','secret_access_key'))

app = Flask(__name__)

@app.route("/")
def index():
    # get everything in the bucket
    bucket = s3.get_bucket( config.get('s3','bucket') ) 
    file_list = [ key.name.split('/') for key in sorted(bucket.list()) ]
    latest_backups = {}
    # build a list of the latest backups per app
    for path_parts in file_list:
        app_name = inflector.titleize(path_parts[1])
        date_str = path_parts[2]
        date = datetime.strptime(date_str,'%Y.%m.%d.%H.%M.%S')
        if (app_name not in latest_backups.keys()) or (date > latest_backups[app_name]['date']):
            status = ''
            age = (datetime.now() - date).days
            if age<1:
                status = 'success'
            elif age<7:
                status = 'warning'
            else:
                status = 'danger'
            latest_backups[app_name] = { 'date': date, 'relative_date': timesince(date), 'status': status }

    return render_template("base.html", latest_backups=latest_backups)

if __name__ == "__main__":
    app.debug = True
    app.run(host='0.0.0.0')
    log.info("Started Server")
