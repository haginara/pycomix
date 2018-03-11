
"""
Listen 31257
<VirtualHost *:31257>
  DocumentRoot "/var/services/web/comix-server"
  AllowEncodedSlashes On
  DirectoryIndex index.php
  AliasMatch ^/welcome.102(.*)$ /var/services/web/comix-server/welcome.php
  AliasMatch ^/manga(.*)$ /var/services/web/comix-server/handler.php
</VirtualHost>

welcome.php {
  <?php
  echo "I am a generous god!\r\n";
  echo "allowDownload=True\r\n";
  echo "allowImageProcess=True";
  ?>
}

handler.php {

}
"""
import os
import json
import codecs
import flask
from functools import wraps
#from flask import request

app = flask.Flask(__name__)
image_ext = ["jpg", "gif", "png", "tif", "bmp", "jpeg", "tiff"]
archive_ext = ["zip", "rar", "cbz", "cbr"]
allows = image_ext + archive_ext
ROOT = 'Z:/data03'
CONTENTS = 'comics'
if not os.path.exists(os.path.join(ROOT, CONTENTS)):
    raise Exception("No Folder")

def check_auth(username, password):
    return username == 'AirComix' and password == 'test'

def authenticate():
    return flask.Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = flask.request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/welcome.102/')
@requires_auth
def welcome():
    welcome_str = """I am a generous god!\r\n""" \
        """allowDownload=True\r\n""" \
        """allowImageProcess=True"""
    return welcome_str

@app.route('/')
@requires_auth
def root():
    #data = json.dumps({'Directories':[CONTENTS],"Files":[]}).strip()
    r = flask.Response(CONTENTS)
    del r.headers['Content-Type']
    return r

@app.route('/<path:req_path>')
@requires_auth
def manga(req_path):
    BASE_DIR = ROOT
    abs_path = os.path.join(ROOT, req_path)
    if not os.path.exists(abs_path):
        app.logger.error("No file: %s", abs_path)
        return flask.abort(404)

    if os.path.isfile(abs_path):
        return flask.send_file(abs_path)
    files = os.listdir(abs_path)
    data = "\n".join(["%s" % name for name in files])
    data = data.encode('utf-8')
    r = flask.Response(data)
    del r.headers['Content-Type']
    return r

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=31258)
