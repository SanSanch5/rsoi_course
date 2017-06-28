import flask
import flask_sqlalchemy
import flask_restless

from settings import DEBUG_MODE, PORT, DB_URI

app = flask.Flask(__name__)
app.config['DEBUG'] = DEBUG_MODE


app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
db = flask_sqlalchemy.SQLAlchemy(app)


class Profile(db.Model):
    __tablename__ = 'profile'

    id = db.Column(db.Integer, primary_key=True)
    password_hash = db.Column(db.String(64), nullable=False)
    phone = db.Column(db.Unicode, nullable=False, unique=True)

    name = db.Column(db.Unicode, nullable=False)
    middle_name = db.Column(db.Unicode, nullable=True, default=None)
    surname = db.Column(db.Unicode, nullable=False)

    role = db.Column(db.Unicode, nullable=False)
    # группы нет у учителя, но для студентов надо делать отдельную проверку, что группа указана
    group = db.Column(db.Unicode, nullable=True, default=None)
    # у студента может (должен) быть указан преподаватель
    tutor_id = db.Column(db.Integer, db.ForeignKey('profile.id'), nullable=True, default=None)

    about = db.Column(db.Unicode, nullable=True, default=None)
    photo = db.Column(db.Unicode, nullable=False)

    # дополнительная необязательная информация
    email = db.Column(db.Unicode, nullable=True, default=None)

db.create_all()

restman = flask_restless.APIManager(app, flask_sqlalchemy_db=db)
restman.create_api(Profile, collection_name='profiles', methods=[
        'GET',
        'POST',
        'PUT',
        'PATCH',
        'DELETE'
    ],
)

if __name__ == '__main__':
    app.run(port=PORT)

