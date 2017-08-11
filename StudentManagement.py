import datetime
import os

import babel.numbers as babel_numbers
from flask import Flask, request, session
from flask_admin import Admin, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_babelex import Babel
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from wtforms.fields import DecimalField

app = Flask(__name__)
app.secret_key = b'\xda~z\xd3Y\x84\xe9vl\xa8\x01\xc8F\xd0\x98\xa2\x8e\xb4\xc2\x00\x18w\xff\xe0'
app.config['DATABASE_FILE'] = 'studentmanagement.sqlite'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + app.config['DATABASE_FILE']
app.config['SQLALCHEMY_ECHO'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
babel = Babel(app)
db = SQLAlchemy(app)


@babel.localeselector
def get_locale():
    if request.args.get('lang'):
        session['lang'] = request.args.get('lang')
    return session.get('lang', 'el')


class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(30))
    last_name = db.Column(db.String(50))
    current_fee = db.Column(db.DECIMAL)
    year_start = db.Column(db.Integer)

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.year_start}-{self.year_start+1})'


class Lesson(db.Model):
    __tablename__ = 'lessons'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, ForeignKey('students.id'))
    student = relationship('Student')
    date = db.Column(db.Date)
    hours = db.Column(db.Integer)
    fee = db.Column(db.DECIMAL)

    def __str__(self):
        return f'{self.student} - {self.date} ({self.hours})'


class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, ForeignKey('students.id'))
    student = relationship('Student')
    date = db.Column(db.Date)
    amount = db.Column(db.DECIMAL)


class ReportsView(BaseView):
    @expose('/')
    def index(self):
        lines = []
        all_lessons = list(db.session.query(Lesson))
        all_payments = list(db.session.query(Payment))
        all_students = list(db.session.query(Student))
        for s in all_students:
            student_paid = sum([p.amount for p in all_payments if p.student_id == s.id])
            student_bought = sum([l.fee * l.hours for l in all_lessons if l.student_id == s.id])
            lines.append({'Student': str(s), 'Balance': round(student_bought - student_paid, 2)})
        return self.render('reports_index.html', lines=lines)


class CustomDecimalField(DecimalField):
    pass


class StudentView(ModelView):
    _current_year = datetime.date.today().year
    form_choices = {
        'year_start': [(i, f"{i}-{i%100+1}") for i in range(_current_year - 2, _current_year + 3)]
    }
    column_formatters = {
        'year_start': lambda v, c, m, p: f"{m.year_start}-{m.year_start%100+1}"
    }


class LessonView(ModelView):
    pass


admin = Admin(app, url='', name='Διαχείριση Μαθητών', template_mode='bootstrap3')
admin.add_view(
    StudentView(Student, db.session, name="Μαθητές", menu_icon_type='glyph', menu_icon_value='glyphicon-user'))
admin.add_view(
    LessonView(Lesson, db.session, name="Μαθήματα", menu_icon_type='glyph', menu_icon_value='glyphicon-education'))
admin.add_view(ModelView(Payment, db.session, name="Πληρωμές", menu_icon_type='glyph', menu_icon_value='glyphicon-eur'))
admin.add_view(
    ReportsView(name="Αναφορά Πληρωμών", endpoint='reports', menu_icon_type='glyph', menu_icon_value='glyphicon-book'))

if __name__ == '__main__':

    # Build a sample db on the fly, if one does not exist yet.
    app_dir = os.path.realpath(os.path.dirname(__file__))
    database_path = os.path.join(app_dir, app.config['DATABASE_FILE'])
    print(database_path)
    if not os.path.exists(database_path):
        db.create_all()
        db.session.commit()

    # Start app
    app.run(port=5011, debug=True)
