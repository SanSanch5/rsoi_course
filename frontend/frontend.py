import requests
import simplejson
from urllib.parse import unquote as urldecode
from werkzeug.utils import secure_filename
from datetime import datetime

import os
import flask

from session_interface import SessionInterface
from settings import DEBUG_MODE, PORT, SERVICES_URI, UPLOAD_FOLDER
from tools import hash_password, render_datetime


app = flask.Flask(__name__)
app.config['DEBUG'] = DEBUG_MODE
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.session_interface = SessionInterface()


@app.route('/', methods=['GET'])
def index():
    return flask.redirect('/lessons')


@app.route('/register', methods=['GET'])
def register():
    if 'redirect_to' in flask.request.args:
        flask.session['redirect_to'] = urldecode(flask.request.args['redirect_to'])

    if flask.session.user_id is not None:
        return flask.redirect('/me')

    # get all tutors
    try:
        tutors = get_tutors()
    except requests.exceptions.RequestException:
        return flask.render_template('error.html', reason='Сервис пользователей недоступен'), 500

    return flask.render_template('profile/register_form.html', tutors=tutors)


@app.route('/register', methods=['POST'])
def post_to_register():
    password_hash = hash_password(flask.request.form['password'])
    name = flask.request.form['name']
    middle_name = flask.request.form['midname']
    surname = flask.request.form['surname']
    phone = flask.request.form['phone']

    role = flask.request.form['role']
    group = None if role == 'tutor' else flask.request.form['group']
    tutor_id = None if role == 'tutor' else flask.request.form.get('tutor', None)

    about = flask.request.form.get('brief', None)
    photo_file = flask.request.files['avatar']
    photo_filename = secure_filename(photo_file.filename)

    # дополнительная необязательная информация
    email = flask.request.form.get('email', None)

    try:
        user_response = requests.post(SERVICES_URI['profiles'], json={
            'name': name,
            'surname': surname,
            'middle_name': middle_name,
            'phone': phone,
            'password_hash': password_hash,
            'email': email,
            'role': role,
            'group': group,
            'tutor_id': tutor_id,
            'about': about,
            'photo': photo_filename,
        })
    except requests.exceptions.RequestException:
        return flask.render_template('error.html', reason='Сервис пользователей недоступен'), 500

    if user_response.status_code == 201:
        user_upload_path = os.path.join(app.config['UPLOAD_FOLDER'], phone)
        if not os.path.exists(user_upload_path):
            os.makedirs(user_upload_path)
        photo_path = os.path.join(user_upload_path, photo_filename)
        photo_file.save(photo_path)

        user = user_response.json()
        flask.session.user_id = user['id']

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
                    {'name': 'phone', 'op': '==', 'val': flask.request.form['phone']},
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
        tutors = get_tutors()
        assert user_response.status_code == 200
        user = user_response.json()
    except requests.exceptions.RequestException:
        user = None

    profile_photo_name = os.path.join(user['phone'], user['photo'])
    return flask.render_template('profile/me.html',
                                 user=user, tutors=tutors,
                                 user_photo_path=flask.url_for(
                                     'static',
                                     filename=os.path.join("img", profile_photo_name)
                                 ))


@app.route('/me', methods=['POST'])
def patch_me():
    user = dict()
    user['password_hash'] = hash_password(flask.request.form['password'])
    user['name'] = flask.request.form['name']
    user['middle_name'] = flask.request.form['midname']
    user['surname'] = flask.request.form['surname']
    user['phone'] = flask.request.form['phone']

    user['group'] = flask.request.form.get('role', None)
    user['about'] = flask.request.form.get('brief', None)

    # дополнительная необязательная информация
    user['email'] = flask.request.form.get('email', None)

    try:
        user_response = requests.patch(SERVICES_URI['profiles'] + '/' + str(flask.session.user_id), json=user)
    except requests.exceptions.RequestException:
        return flask.render_template('error.html', reason='Сервис пользователей недоступен'), 500

    if user_response.status_code == 200:
        user = user_response.json()
        profile_photo_name = os.path.join(user['phone'], user['photo'])
        return flask.render_template('profile/me.html',
                                     user=user,
                                     user_photo_path=flask.url_for(
                                         'static',
                                         filename=os.path.join("img", profile_photo_name)
                                     ))

    return flask.render_template('error.html', reason=user_response.json()), 500


@app.route('/lessons', methods=['GET'])
def get_lessons():
    if flask.session.user_id is None:
        flask.session['redirect_to'] = '/lessons'
        return flask.redirect('/sign_in')

    user_role = None
    tutor_id = None
    if flask.session.user_id is not None:
        try:
            user_response = requests.get(SERVICES_URI['profiles'] + '/' + str(flask.session.user_id))
            if user_response.status_code != 200:
                return flask.render_template('error.html', reason=user_response.json()), 500

            user = user_response.json()
            user_role = user['role']
            tutor_id = user['tutor_id'] if user_role == 'student' else user['id']
        except requests.exceptions.RequestException:
            pass

    try:
        lessons_response = requests.get(SERVICES_URI['lessons'], params={
            'q': simplejson.dumps({
                'filters': [
                    {'name': 'tutor_id', 'op': '==', 'val': tutor_id},
                ],
            }),
        })
        assert lessons_response.status_code == 200
        lessons = lessons_response.json()
        lessons = lessons['objects']
    except requests.exceptions.RequestException:
        lessons = None

    return flask.render_template('tasks/lessons.html', user_role=user_role, lessons=lessons)


@app.route('/lessons', methods=['POST'])
def create_lesson():
    lesson = dict()
    lesson['number'] = flask.request.form['new_lesson']
    lesson['tutor_id'] = flask.session.user_id
    lesson['created_at'] = render_datetime(datetime.now())

    try:
        lesson_response = requests.post(SERVICES_URI['lessons'], json=lesson)
    except requests.exceptions.RequestException:
        return flask.render_template('error.html', reason='Сервис заданий недоступен'), 500

    if lesson_response.status_code == 201:
        return flask.redirect("/lessons/%s" % lesson['number'], code=303)

    return flask.render_template('error.html', reason=lesson_response.json()), 500


@app.route('/lessons/<number>', methods=['GET'])
def get_lesson(number):
    if flask.session.user_id is None:
        flask.session['redirect_to'] = "/lessons/%d" % number
        return flask.redirect('/sign_in')

    user_role = None
    tutor_id = None
    task = None
    if flask.session.user_id is not None:
        try:
            user_response = requests.get(SERVICES_URI['profiles'] + '/' + str(flask.session.user_id))
            if user_response.status_code != 200:
                return flask.render_template('error.html', reason=user_response.json()), 500

            user = user_response.json()
            user_role = user['role']
            tutor_id = user['tutor_id'] if user_role == 'student' else user['id']
        except requests.exceptions.RequestException:
            pass

    try:
        lesson_response = requests.get(SERVICES_URI['lessons'], params={
            'q': simplejson.dumps({
                'filters': [
                    {'name': 'tutor_id', 'op': '==', 'val': tutor_id},
                    {'name': 'number', 'op': '==', 'val': number},
                ],
            }),
        })
        assert lesson_response.status_code == 200
        lesson = lesson_response.json()['objects'][0]

        if lesson['task_id'] is not None:
            task_response = requests.get(SERVICES_URI['profiles'] + "/%d" % lesson['task_id'])
            assert task_response.status_code == 200
            task = task_response.json()
    except requests.exceptions.RequestException:
        lesson = None

    return flask.render_template('tasks/lesson.html',
                                 user_role=user_role,
                                 lesson=lesson,
                                 task=task)


def get_tutors():
    tutors_response = requests.get(SERVICES_URI['profiles'], params={
        'q': simplejson.dumps({
            'filters': [
                {'name': 'role', 'op': '==', 'val': 'tutor'},
            ],
        }),
    })
    assert tutors_response.status_code == 200
    tutors = tutors_response.json()

    return tutors['objects']

if __name__ == '__main__':
    app.run(port=PORT)

