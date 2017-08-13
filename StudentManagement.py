import datetime
import json
import os

import babel.numbers as babel_numbers
import dateutil.parser
from flask import Flask, request, session
from flask_admin import Admin, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.form import AdminModelConverter
from flask_admin.form import BaseForm
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
        return self.render('reports/index.html', lines=lines)


def _current_year():
    return datetime.date.today().year


class StudentView(ModelView):
    can_export = True

    form_choices = {
        'year_start': [(str(i), f"{i}-{i%100+1}") for i in range(_current_year() - 2, _current_year() + 3)]
    }
    column_formatters = {
        'current_fee': lambda v, c, m, p: f"{babel_numbers.format_currency(m.current_fee, 'EUR', locale='el_GR')}",
        'year_start': lambda v, c, m, p: f"{m.year_start}-{m.year_start%100+1}" if m.year_start else ''
    }
    form_overrides = {
        'current_fee': DecimalField
    }
    form_args = {
        'current_fee': {
            'use_locale': True
        }
    }

    def scaffold_form(self):
        form_class = super().scaffold_form()
        form_class.Meta.locales = ['el_GR']
        return form_class


class LessonModelConverter(AdminModelConverter):
    def get_form(self, model, base_class=BaseForm, only=None, exclude=None, field_args=None):
        return super().get_form(model, base_class, only, exclude, field_args)

    def convert(self, model, mapper, name, prop, field_args, hidden_pk):
        return super().convert(model, mapper, name, prop, field_args, hidden_pk)


class LessonView(ModelView):
    can_export = True
    model_form_converter = LessonModelConverter


admin = Admin(app, url='', name='Διαχείριση Μαθητών', template_mode='bootstrap3')
admin.add_view(
    StudentView(Student, db.session, name="Μαθητές", menu_icon_type='glyph', menu_icon_value='glyphicon-user'))
admin.add_view(
    LessonView(Lesson, db.session, name="Μαθήματα", menu_icon_type='glyph', menu_icon_value='glyphicon-education'))
admin.add_view(ModelView(Payment, db.session, name="Πληρωμές", menu_icon_type='glyph', menu_icon_value='glyphicon-eur'))
admin.add_view(
    ReportsView(name="Αναφορά Πληρωμών", endpoint='reports', menu_icon_type='glyph', menu_icon_value='glyphicon-book'))


def insert_sample_data():
    sample_data_filename = 'sample_data.json'
    if not os.path.exists(sample_data_filename):
        return
    with open(sample_data_filename) as f:
        data = json.load(f)
        for student in data['students']:
            s = Student()
            s.first_name = student['first_name']
            s.last_name = student['last_name']
            s.year_start = _current_year()
            s.current_fee = 0.0
            min_date = None
            max_date = None
            for lesson in student['lessons']:
                l = Lesson()
                l.date = dateutil.parser.parse(lesson['date'])
                l.hours = lesson['hours']
                l.student = s
                if min_date is None or min_date > l.date:
                    min_date = l.date
                if max_date is None or max_date < l.date:
                    max_date = l.date
                db.session.add(l)
            if min_date is not None and max_date is not None:
                # assert (max_date - min_date).days < 365
                print(f'{s.first_name} {s.last_name} ({min_date.year}-{max_date.year})')
            db.session.add(s)
            db.session.commit()


if __name__ == '__main__':

    # Build a sample db on the fly, if one does not exist yet.
    app_dir = os.path.realpath(os.path.dirname(__file__))
    database_path = os.path.join(app_dir, app.config['DATABASE_FILE'])
    print(database_path)
    if not os.path.exists(database_path):
        db.create_all()
        db.session.commit()
        insert_sample_data()
    # Start app
    app.run(port=5011, debug=True)
