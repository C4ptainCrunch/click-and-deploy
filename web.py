from flask import Flask, render_template, request
import settings
import lib
from rq import Queue
from redis import Redis
import json

import sys

JSONError = json.JSONDecodeError if sys.version_info.major >= 3 else ValueError

flapp = Flask(__name__)
flapp.debug = settings.DEBUG


redis_conn = Redis()
q = Queue(connection=redis_conn)


@flapp.route("/")
def hello():
    files = settings.APPS_DIR.listdir('*.app')
    apps = map(lambda app_file: lib.json_to_app(app_file), files)
    return render_template('hello.html', apps=apps)


@flapp.route("/app/<app_id>/")
def show_app(app_id):
    app = lib.app_id_to_data(app_id)
    return render_template('app.html', app=app)


@flapp.route("/app/<app_id>/deploy/", methods=['GET', 'POST'])
def deploy_app(app_id):
    event_type = request.headers.get('X-GitHub-Event', 'manual')
    if event_type not in ('push', 'manual'):
        return "Not a usefull event X-GitHub-Event : {}".format(event_type)
    if event_type == 'push':
        try:
            data = json.loads(request.data)
            if data['ref'].split('/')[-1] != "master":
                return "Not a usefull branch : {}".format(data['ref'])
        except (JSONError, KeyError) as e:
            print(e)
    lib.app_exists(app_id)
    q.enqueue(lib.deploy_app, app_id)
    return 'Task added in queue, should be deployed soon.<br> <a href="/">Go back to app</a>'


if __name__ == "__main__":
    flapp.run()
