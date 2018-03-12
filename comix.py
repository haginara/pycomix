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

to_hex = lambda x: hex(ord(x))

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

def get_ext(path_name):
    ext = os.path.splitext(path_name)[-1]
    if ext:
        return ext[1:]
    return ext

def list_directories(path):
    data = {'Directories': [], 'Files': []}
    for name in os.listdir(path):
        name = name.encode('utf-8')
        app.logger.debug("Type: %s, Name: %s", type(name), name)
        data['Directories'].append(name)
    response = flask.Response(json.dumps(data, ensure_ascii=False), headers=None)
    return response

def get_real_path(base, abs_path):
    abs_path = unquote(abs_path)
    real_path = os.path.join(base, abs_path)
    app.logger.debug("real_path: %s", real_path)
    return real_path

def get_files_in_zip_path(zipname, path):
    """get list of files in folder in zip file """
    data = {'Directories':[], 'Files': []}
    with zipfile.ZipFile(zipname) as zf:
        for name in zf.namelist():
            name = name.decode('euc-kr').encode('utf-8')
            pardir, basename = os.path.split(name)
            if basename and path == pardir:
                logger.info("get_files_in_zip_path: %s, %s", pardir, basename)
                data['Files'].append(basename)
    if len(data['Files']):
        response = flask.Response(json.dumps(data, ensure_ascii=False), headers=None)
        return response

    return ('', 204)

def get_file_in_zip_file(path):
    """ Only zip files are supported <path>/file.zip/1/01.jpg """
    zip_path, in_zip_path = path.split('.zip')
    zip_path += '.zip'
    in_zip_path = in_zip_path[1:]
    try:
        in_zip_path = in_zip_path.encode('utf-8')
    except Exception as e:
        logger.info("Failed to encode: %s", in_zip_path)

    logger.info('zip_path: %s, %s(%s)', zip_path, in_zip_path, type(in_zip_path))

    if not os.path.exists(zip_path):
        app.logger.error("No file: %s", zip_path)
        return ('', 204)

    if not get_ext(in_zip_path):
        """ /file.zip/01/"""
        return get_files_in_zip_path(zip_path, in_zip_path)

    ## Render single file
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            encoded_name = name.decode('euc-kr').encode('utf-8')
            logger.info("%s(%s), %s(%s), %s, %s", encoded_name, type(encoded_name), in_zip_path, type(in_zip_path), [to_hex(c) for c in name], [to_hex(c) for c in in_zip_path])
            if encoded_name == in_zip_path:
                with zf.open(name) as f:
                    bytesIO = BytesIO()
                    bytesIO.write(f.read())
                    bytesIO.seek(0)
                    return flask.send_file(bytesIO, attachment_filename=os.path.basename(in_zip_path), as_attachment=True)
        logger.error("No file Name: %s", in_zip_path)
        return ('', 204)

def list_zip_files(zip_path):
    """ Response list of files in zip file """
    with zipfile.ZipFile(zip_path) as zf:
        data = {'Directories': [], 'Files': []}
        app.logger.info("Loaded the zip file: %s", zip_path)
        dirs = [name for name in zf.namelist() if name.endswith('/')]
        subdirs = set([name.split('/')[0] for name in dirs])
        if subdirs:
            for dirname in subdirs:
                dirname = dirname.decode('euc-kr').encode('utf-8')
                app.logger.debug('list_zip_files: %s, %s', dirname, [to_hex(c) for c in dirname])
                data['Directories'].append(dirname)
            data = json.dumps(data, ensure_ascii=False)
            r = flask.Response(data, headers=None)
            return r
    ## No folder in zip file
    return get_files_in_zip_path(zip_path, '')

@app.route('/')
@requires_auth
def root():
    app.logger.info("root directory")
    data = json.dumps({'Directories':[CONTENTS],"Files":[]}, ensure_ascii=False)
    r = flask.Response(data, headers=None)
    return r

@app.route('/welcome.102/')
@requires_auth
def welcome():
    app.logger.info("Welcome")
    welcome_str = """Hello!\r\n""" \
        """allowDownload=True\r\n""" \
        """autoResizing=False\r\n""" \
        """minVersion=1.3\r\n""" \
        """supportJson=True"""
    return welcome_str

@app.route('/<path:req_path>')
@requires_auth
def location(req_path):
    BASE_DIR = ROOT
    ROOT_CONTENTS = os.path.join(BASE_DIR, CONTENTS)
    abs_path = get_real_path(BASE_DIR, req_path)
    if get_ext(abs_path) == 'thm':
        return ('', 204)

    ## List up Root folder
    if abs_path == ROOT_CONTENTS:
        return list_directories(ROOT_CONTENTS)

    ##  Get files in zip file
    if get_ext(abs_path) not in archive_ext and  '.zip' in abs_path:
        """ Only zip files are supported <path>/file.zip/1/01.jpg"""
        return get_file_in_zip_file(abs_path)

    if not os.path.exists(abs_path):
        logger.error("No Path: %s", abs_path)
        return ('', 204)

    if os.path.isfile(abs_path):
        if get_ext(abs_path) in archive_ext:
            """ List zip files """
            logger.info("Archive File: %s", abs_path)
            return list_zip_files(abs_path)
        ## Render Image Files
        return flask.send_file(abs_path)

    data = {'Directories': [], 'Files': []}
    ## Send list of files
    if os.path.isdir(abs_path):
        for name in os.listdir(abs_path):
            if os.path.isdir(os.path.join(abs_path, name)) or get_ext(name) == 'zip':
                data['Directories'].append(name)
            elif get_ext(name) not in archive_ext:
                data['Files'].append(name)
        logger.info("File: %s", data)
        response = flask.Response(json.dumps(data, ensure_ascii=False), headers=None)
        return response

if __name__ == '__main__':
    app.run(host=CONF['HOST'], port=CONF['PORT'], debug=True)
