import datetime
import json
import os
import random

import babel.numbers as babel_numbers
import flask_login as login
from dateutil.parser import parse as dateparse
from dateutil.relativedelta import relativedelta
from flask import Flask, request, session, redirect, url_for
from flask_admin import Admin, AdminIndexView, BaseView, helpers, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.form import AdminModelConverter
from flask_admin.form import BaseForm
from flask_babelex import Babel
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from sqlalchemy.event import listens_for
from sqlalchemy.orm import relationship
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import form, fields, validators
from wtforms.fields import DecimalField

app = Flask(__name__)
app.secret_key = b'\xda~z\xd3Y\x84\xe9vl\xa8\x01\xc8F\xd0\x98\xa2\x8e\xb4\xc2\x00\x18w\xff\xe0'
app.config['DATABASE_FILE'] = 'studentmanagement.sqlite'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + app.config['DATABASE_FILE']
app.config['SQLALCHEMY_ECHO'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True
babel = Babel(app)
db = SQLAlchemy(app)


@babel.localeselector
def get_locale():
    if request.args.get('lang'):
        session['lang'] = request.args.get('lang')
    return session.get('lang', 'el')


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(35))
    last_name = db.Column(db.String(35))
    username = db.Column(db.String(35), unique=True)
    email = db.Column(db.String(120))
    password = db.Column(db.String(64))

    @property
    def display_name(self):
        return self.first_name + " " + self.last_name

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    def __str__(self):
        return self.username

    def __unicode__(self):
        return self.username


class LoginForm(form.Form):
    login = fields.StringField(validators=[validators.required()])
    password = fields.PasswordField(validators=[validators.required()])

    def validate_login(self, field):
        user = self.get_user()

        if user is None:
            raise validators.ValidationError("Invalid username or password")

        if not check_password_hash(user.password, self.password.data):
            raise validators.ValidationError("Invalid username or password")

    def get_user(self):
        return db.session.query(User).filter_by(username=self.login.data).first()


class AuthorizedModelView(ModelView):
    def is_accessible(self):
        return login.current_user.is_authenticated


class MyAdminIndexView(AdminIndexView):
    def __init__(self, name=None, category=None,
                 endpoint=None, url=None,
                 template='admin/index.html',
                 menu_class_name=None,
                 menu_icon_type=None,
                 menu_icon_value=None):
        super().__init__(name=name, category=category, endpoint=endpoint, url=url, template=template,
                         menu_class_name=menu_class_name, menu_icon_type=menu_icon_type,
                         menu_icon_value=menu_icon_value)

    @expose('/')
    def index(self):
        if not login.current_user.is_authenticated:
            return redirect(url_for('.login_view'))
        return super().index()

    @expose('/login/', methods=('GET', 'POST'))
    def login_view(self):
        # handle user login
        the_form = LoginForm(request.form)
        if helpers.validate_form_on_submit(the_form):
            user = the_form.get_user()
            login.login_user(user)

        if login.current_user.is_authenticated:
            return redirect(url_for('.index'))
        # link = '<p>Don\'t have an account? <a href="' + url_for('.register_view') + '">Click here to register.</a></p>'
        self._template_args['form'] = the_form
        # self._template_args['link'] = link
        return super().index()

    # @expose('/register/', methods=('GET', 'POST'))
    # def register_view(self):
    #     form = RegistrationForm(request.form)
    #     if helpers.validate_form_on_submit(form):
    #         user = User()
    #
    #         form.populate_obj(user)
    #         # we hash the users password to avoid saving it as plaintext in the db,
    #         # remove to use plain text:
    #         user.password = generate_password_hash(form.password.data)
    #
    #         db.session.add(user)
    #         db.session.commit()
    #
    #         login.login_user(user)
    #         return redirect(url_for('.index'))
    #     link = '<p>Already have an account? <a href="' + url_for('.login_view') + '">Click here to log in.</a></p>'
    #     self._template_args['form'] = form
    #     self._template_args['link'] = link
    #     return super().index()

    @expose('/logout/')
    def logout_view(self):
        login.logout_user()
        return redirect(url_for('.index'))


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


@listens_for(Lesson, 'before_insert')
def before_insert_lesson(mapper, connection, target):
    if target.fee is None:
        target.fee = target.student.current_fee


class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, ForeignKey('students.id'))
    student = relationship('Student')
    date = db.Column(db.Date)
    amount = db.Column(db.DECIMAL)


class ReportsView(BaseView):
    def is_accessible(self):
        return login.current_user.is_authenticated

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


class StudentView(AuthorizedModelView):
    can_export = True
    create_modal = True
    edit_modal = True

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


class LessonView(AuthorizedModelView):
    can_export = True
    model_form_converter = LessonModelConverter
    column_filters = ['student', 'date']
    column_formatters = {
        'fee': lambda v, c, m, p: f"{babel_numbers.format_currency(m.fee, 'EUR', locale='el_GR')}"
    }
    form_overrides = {
        'fee': DecimalField
    }


admin = Admin(app, index_view=MyAdminIndexView(url=''), name='Διαχείριση Μαθητών', template_mode='bootstrap3')
admin.add_view(
    StudentView(Student, db.session, name="Μαθητές", menu_icon_type='glyph', menu_icon_value='glyphicon-user'))
admin.add_view(
    LessonView(Lesson, db.session, name="Μαθήματα", menu_icon_type='glyph', menu_icon_value='glyphicon-education'))
admin.add_view(
    AuthorizedModelView(Payment, db.session, name="Πληρωμές", menu_icon_type='glyph', menu_icon_value='glyphicon-eur'))
admin.add_view(
    ReportsView(name="Αναφορά Πληρωμών", endpoint='reports', menu_icon_type='glyph', menu_icon_value='glyphicon-book'))


# Initialize flask-login
def init_login():
    login_manager = login.LoginManager()
    login_manager.init_app(app)

    # Create user loader function
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.query(User).get(user_id)


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
            min_date = None
            max_date = None
            s.current_fee = random.randint(1, 10) * 5.0
            for lesson in student['lessons']:
                l = Lesson()
                l.date = dateparse(lesson['date'])
                l.hours = lesson['hours']
                l.student = s
                l.fee = s.current_fee
                if min_date is None or min_date > l.date:
                    min_date = l.date
                if max_date is None or max_date < l.date:
                    max_date = l.date
                db.session.add(l)
            if min_date is not None and max_date is not None:
                # assert (max_date - min_date).days < 365
                print(f'{s.first_name} {s.last_name} ({min_date.year}-{max_date.year})')
                s.year_start = (max_date + relativedelta(months=-8)).year
            else:
                s.year_start = _current_year()
            db.session.add(s)
            db.session.commit()
        for user in data['users']:
            u = User()
            u.first_name = user['first_name']
            u.last_name = user['last_name']
            u.email = user['email']
            u.username = user['username']
            u.password = generate_password_hash(user['password'])
            db.session.add(u)
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
    init_login()
    app.run(port=5011, debug=True)
