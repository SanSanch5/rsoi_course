import requests
import simplejson
from urllib.parse import unquote as urldecode
from werkzeug.utils import secure_filename

import os
import flask

from session_interface import SessionInterface
from settings import DEBUG_MODE, PORT, SERVICES_URI, UPLOAD_FOLDER
from tools import hash_password


app = flask.Flask(__name__)
app.config['DEBUG'] = DEBUG_MODE
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.session_interface = SessionInterface()


@app.route('/', methods=['GET'])
def index():
    return flask.redirect('/me')


@app.route('/register', methods=['GET'])
def register():
    if 'redirect_to' in flask.request.args:
        flask.session['redirect_to'] = urldecode(flask.request.args['redirect_to'])

    if flask.session.user_id is not None:
        return flask.redirect('/me')

    return flask.render_template('profile/register_form.html')


@app.route('/register', methods=['POST'])
def post_to_register():
    try:
        password_hash = hash_password(flask.request.form['password'])
        name = flask.request.form['name']
        middle_name = flask.request.form['midname']
        surname = flask.request.form['surname']
        phone = flask.request.form['phone']

        role = flask.request.form['role']
        group = None if role == 'tutor' else flask.request.form['group']
        about = flask.request.form.get('brief', None)
        photo_file = flask.request.files['avatar']
        photo_filename = secure_filename(photo_file.filename)

        # дополнительная необязательная информация
        email = flask.request.form.get('email', None)

        user_response = requests.post(SERVICES_URI['profiles'], json={
            'name': name,
            'surname': surname,
            'middle_name': middle_name,
            'phone': phone,
            'password_hash': password_hash,
            'email': email,
            'role': role,
            'group': group,
            'about': about,
            'photo': photo_filename,
        })
    except requests.exceptions.RequestException:
        return flask.render_template('error.html', reason='Сервис пользователей недоступен'), 500

    if user_response.status_code == 201:
        user = user_response.json()
        flask.session.user_id = user['id']

        user_upload_path = os.path.join(app.config['UPLOAD_FOLDER'], user['id'])
        if not os.path.exists(user_upload_path):
            os.makedirs(user_upload_path)
        photo_path = os.path.join(user_upload_path, photo_filename)
        photo_file.save(photo_path)

        return flask.redirect(flask.session.pop('redirect_to', '/me'), code=303)

    return flask.render_template('error.html', reason=user_response.json()), 500


@app.route('/sign_in', methods=['GET'])
def sign_in():
    if 'redirect_to' in flask.request.args:
        flask.session['redirect_to'] = urldecode(flask.request.args['redirect_to'])

    if flask.session.user_id is not None:
        return flask.redirect('/me')

    return flask.render_template('profile/authorize_form.html')


@app.route('/sign_in', methods=['POST'])
def post_to_sign_in():
    try:
        user_response = requests.get(SERVICES_URI['profiles'], params={
            'q': simplejson.dumps({
                'filters': [
                    {'name': 'login', 'op': '==', 'val': flask.request.form['login']},
                    {'name': 'password_hash', 'op': '==', 'val': hash_password(flask.request.form['password'])},
                ],
                'single': True,
            }),
        })
    except requests.exceptions.RequestException:
        return flask.render_template('error.html', reason='Сервис пользователей недоступен'), 500

    if user_response.status_code == 200:
        user = user_response.json()
        flask.session.user_id = user['id']
        return flask.redirect(flask.session.pop('redirect_to', '/me'), code=303)

    return flask.render_template('error.html', reason=user_response.json()), 500


@app.route('/me', methods=['GET'])
def me():
    if flask.session.user_id is None:
        flask.session['redirect_to'] = '/me'
        return flask.redirect('/sign_in')

    try:
        user_response = requests.get(SERVICES_URI['profiles'] + '/' + str(flask.session.user_id))
        assert user_response.status_code == 200
        user = user_response.json()
    except requests.exceptions.RequestException:
        user = None

    return flask.render_template('profile/me.html', user=user)


@app.route('/me', methods=['POST'])
def patch_me():
    user = {}
    if 'password' in flask.request.form and flask.request.form['password']:
        user['password_hash'] = hash_password(flask.request.form['password'])
    if 'name' in flask.request.form:
        user['name'] = flask.request.form['name'] or None
    if 'phone' in flask.request.form:
        user['phone'] = flask.request.form['phone'] or None
    if 'email' in flask.request.form:
        user['email'] = flask.request.form['email'] or None

    try:
        user_response = requests.patch(SERVICES_URI['profiles'] + '/' + str(flask.session.user_id), json=user)
    except requests.exceptions.RequestException:
        return flask.render_template('error.html', reason='Сервис пользователей недоступен'), 500

    if user_response.status_code == 200:
        user = user_response.json()
        return flask.render_template('profile/me.html', user=user)

    return flask.render_template('error.html', reason=user_response.json()), 500

if __name__ == '__main__':
    app.run(port=PORT)

