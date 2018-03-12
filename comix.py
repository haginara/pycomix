# -*- coding: utf-8 -*-
#!/usr/bin/env python

import os
import sys
import json
import logging
import zipfile
import flask

from io import BytesIO
from functools import wraps
#from flask import request
if sys.version_info.major == 3:
    from urllib.parse import *
    from io import StringIO
else:
    from urllib import *
    import StringIO

__version__ = (0, 2, 0)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CONF = json.loads(open('comix.json', 'r').read())

image_ext = ["jpg", "gif", "png", "tif", "bmp", "jpeg", "tiff"]
archive_ext = ["zip", "rar", "cbz", "cbr"]
allows = image_ext + archive_ext
ROOT = CONF['ROOT']
CONTENTS = CONF['CONTENTS']
os.sep = '/'

app = flask.Flask(__name__)


if not os.path.exists(os.path.join(ROOT, CONTENTS)):
    raise Exception("No Folder")

def check_auth(username, password):
    return username == 'AirComix' and password == CONF['PASSWORD']

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
            logger.error("Failed to login")
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/welcome.102/')
@requires_auth
def welcome():
    logger.error("Welcome")
    welcome_str = """Hello!\r\n""" \
        """allowDownload=True\r\n""" \
        """autoResizing=False\r\n""" \
        """minVersion=1.3\r\n""" \
        """supportJson=True"""
    return welcome_str

@app.route('/')
@requires_auth
def root():
    logger.debug("root directory")
    data = json.dumps({'Directories':[CONTENTS],"Files":[]}, ensure_ascii=False)
    r = flask.Response(data, headers=None)
    return r

def get_ext(path_name):
    ext = os.path.splitext(path_name)[-1]
    if ext:
        return ext[1:]
    return ext

def list_directories(path):
    data = {'Directories': [], 'Files': []}
    for name in os.listdir(path):
        name = name.encode('utf-8')
        if get_ext(name) not in archive_ext:
            data['Directories'].append(name)
    response = flask.Response(json.dumps(data, ensure_ascii=False), headers=None)
    return response

def get_real_path(base, abs_path):
    abs_path = unquote(abs_path)
    real_path = os.path.join(base, abs_path)
    logger.info("ABS_PATH: %s, %s", real_path, [ord(c) for c in real_path])
    return real_path

@app.route('/<path:req_path>')
@requires_auth
def manga(req_path):
    BASE_DIR = ROOT
    ROOT_CONTENTS = os.path.join(BASE_DIR, CONTENTS)
    abs_path = get_real_path(BASE_DIR, req_path)
    data = {'Directories': [], 'Files': []}

    if abs_path == ROOT_CONTENTS:
        return list_directories(ROOT_CONTENTS)

    if get_ext(abs_path) not in archive_ext and  '.zip' in abs_path:
        return get_file_in_zip_file(abs_path)

    if not os.path.exists(abs_path):
        logger.error("No Path: %s", abs_path)
        return ('', 204)
    ## Render Image Files
    if os.path.isfile(abs_path):
        if get_ext(abs_path) in archive_ext:
            logger.info("Archive File: %s", abs_path)
            return list_zip_files(abs_path)
        return flask.send_file(abs_path)
    ## Send list of files
    if os.path.isdir(abs_path):
        for name in os.listdir(abs_path):
            #if os.path.isdir(os.path.join(abs_path, name)) or get_ext(name) == 'zip':
            if os.path.isdir(os.path.join(abs_path, name)):
                data['Directories'].append(name)
            elif get_ext(name) not in archive_ext:
                data['Files'].append(name)
        logger.info("File: %s", data)
        response = flask.Response(json.dumps(data, ensure_ascii=False), headers=None)
        return response

def get_file_in_zip_file(path):
    """
    """
    zip_path, in_zip_path = path.split('.zip')
    zip_path += '.zip'
    in_zip_path = in_zip_path[1:]
    logger.info('zip_path: %s, %s', zip_path, [ord(c) for c in in_zip_path])
    if not os.path.exists(zip_path):
        app.logger.error("No file: %s", zip_path)
        return ('', 204)
    with zipfile.ZipFile(zip_path) as zf:
        in_zip_path = in_zip_path.encode('utf-8')
        for name in zf.namelist():
            logger.debug("%s, %s, %s, %s", name, in_zip_path, [ord(c) for c in name], [ord(c) for c in in_zip_path])
            if name == in_zip_path:
                logger.info("Loaded :%s", str(name))
                with zf.open(name) as f:
                    bytesIO = BytesIO()
                    bytesIO.write(f.read())
                    bytesIO.seek(0)
                    return flask.send_file(bytesIO, attachment_filename=os.path.basename(in_zip_path), as_attachment=True)
        logger.error("No file Name: %s", in_zip_path)
        return ('', 204)

def list_zip_files(zip_path):
    data = {'Directories': [], 'Files': []}
    with zipfile.ZipFile(zip_path) as zf:
        dirs = [name for name in zf.namelist() if name.endswith('/')]
        subdirs = set([name.split('/')[0] for name in dirs])
        for dirname in subdirs:
            dirname = dirname.decode('latin-1')
            logger.debug('list_zip_files: %s, %s', dirname, [hex(ord(c)) for c in dirname])
            data['Directories'].append(dirname)
        data = json.dumps(data, ensure_ascii=False)
        r = flask.Response(data, headers=None)
        return r

if __name__ == '__main__':
    app.run(host=CONF['HOST'], port=CONF['PORT'], debug=True)
