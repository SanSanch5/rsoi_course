import flask
import flask_sqlalchemy
import flask_restless
from flask_migrate import Migrate

from settings import PORT, DEBUG_MODE, DB_URI

app = flask.Flask(__name__)
app.config['DEBUG'] = DEBUG_MODE

app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
db = flask_sqlalchemy.SQLAlchemy(app)
migrate = Migrate(app, db)


class Lesson(db.Model):
    __tablename__ = 'lesson'

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)
    tutor_id = db.Column(db.Integer, nullable=False)
    answers = db.relationship('LessonAnswer', cascade='all, delete-orphan')

    created_at = db.Column(db.DateTime, nullable=False)
    closed_at = db.Column(db.DateTime, nullable=True, default=None)

    __table_args__ = (db.UniqueConstraint('number', 'tutor_id', name='tutor_lesson_number_uc'),)


class Task(db.Model):
    __tablename__ = 'task'

    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.UnicodeText, nullable=False)

    created_at = db.Column(db.DateTime, nullable=False)
    last_updated_at = db.Column(db.DateTime, nullable=False)


class LessonAnswer(db.Model):
    __tablename__ = 'lesson_answer'

    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=False)
    student_id = db.Column(db.Integer, nullable=False)
    answer = db.Column(db.UnicodeText, nullable=False)
    mark = db.Column(db.Integer, nullable=True, default=None)

    created_at = db.Column(db.DateTime, nullable=False)
    last_updated_at = db.Column(db.DateTime, nullable=False)


db.create_all()

restman = flask_restless.APIManager(app, flask_sqlalchemy_db=db)
restman.create_api(Lesson,
                   collection_name='lessons',
                   methods=[
                       'GET',
                       'POST',
                       'PUT',
                       'PATCH',
                       'DELETE'
                   ],)

restman.create_api(Task,
                   collection_name='tasks',
                   methods=[
                       'GET',
                       'POST',
                       'PUT',
                       'PATCH',
                       'DELETE'
                   ],)

if __name__ == '__main__':
    app.run(port=PORT)
