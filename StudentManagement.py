import base64
import datetime
import json
import os
import random

import babel.numbers as babel_numbers
import flask_login as login
import requests
from dateutil.parser import parse as dateparse
from dateutil.relativedelta import relativedelta
from flask import Flask, request, session, redirect, url_for
from flask_admin import Admin, AdminIndexView, BaseView, helpers, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.form import AdminModelConverter
from flask_admin.form import BaseForm
from flask_babelex import Babel
from sqlalchemy.event import listens_for
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import form, fields, validators
from wtforms.fields import DecimalField

from Models import db, User, Student, Lesson, Payment, Location, Subject, Grade

app = Flask(__name__)
app.secret_key = base64.b64decode('2n5601mE6XZsqAHIRtCYoo60wgAYd//g')
if 'DATABASE_URL' in os.environ:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
else:
    app.config['DATABASE_FILE'] = 'studentmanagement.sqlite'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + app.config['DATABASE_FILE']
app.config['SQLALCHEMY_ECHO'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True
db.app = app
db.init_app(app)
babel = Babel(app)


@babel.localeselector
def get_locale():
    if request.args.get('lang'):
        session['lang'] = request.args.get('lang')
    return session.get('lang', 'el')


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


@listens_for(Lesson, 'before_insert')
def before_insert_lesson(mapper, connection, target):
    if target.fee is None:
        target.fee = target.student.current_fee


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
            lines.append({'Student': s, 'Balance': round(student_bought - student_paid, 2)})
        return self.render('reports/index.html', lines=lines, babel_numbers=babel_numbers)


def _current_year():
    return datetime.date.today().year


class StudentView(AuthorizedModelView):
    can_export = True

    form_choices = {
        'year_start': [(str(i), f"{i}-{i%100+1}") for i in range(_current_year() - 2, _current_year() + 3)],
        'location': [(loc.id, loc.name) for loc in db.session.query(Location).all()]
    }
    column_formatters = {
        'current_fee': lambda v, c, m, p: f"{babel_numbers.format_currency(m.current_fee, 'EUR', locale='el_GR')}",
        'year_start': lambda v, c, m, p: f"{m.year_start}-{m.year_start%100+1}" if m.year_start else ''
    }
    form_overrides = {
        'current_fee': DecimalField
    }
    column_list = [
        'first_name',
        'last_name',
        'current_fee',
        'year_start',
        'location',
        'subject',
        'grade',
        'notes'
    ]
    column_searchable_list = ['first_name', 'last_name']
    column_filters = ['location', 'subject', 'grade', 'year_start']
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
admin.add_view(AuthorizedModelView(Location, db.session, name='Τοποθεσίες', category="Πίνακες συστήματος"))
admin.add_view(AuthorizedModelView(Subject, db.session, name='Μαθήματα', category="Πίνακες συστήματος"))
admin.add_view(AuthorizedModelView(Grade, db.session, name='Τάξεις', category="Πίνακες συστήματος"))


# Initialize flask-login
def init_login():
    login_manager = login.LoginManager()
    login_manager.init_app(app)

    # Create user loader function
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.query(User).get(user_id)


def insert_sample_data():
    if 'INITIAL_DATA_URL' not in os.environ:
        return

    initial_data_location = os.environ['INITIAL_DATA_URL']
    if initial_data_location.startswith('http://') or initial_data_location.startswith('https://'):
        data = requests.get(initial_data_location).json()
    else:
        initial_data_location_full = os.path.join(os.getcwd(), initial_data_location)
        if not os.path.exists(initial_data_location_full):
            return
        with open(initial_data_location_full) as f:
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

    for idx, loc_name in enumerate(['Σύρος', 'Νάξος']):
        loc = Location()
        loc.id = idx + 1
        loc.name = loc_name
        db.session.add(loc)
    db.session.commit()

    for idx, subj_name in enumerate(['Βιολογία', 'Χημεία']):
        subj = Subject()
        subj.id = idx + 1
        subj.name = subj_name
        db.session.add(subj)
    db.session.commit()

    for idx, grd_name in enumerate(["Α' Λυκείου", "Β' Λυκείου", "Γ' Λυκείου", "Απόφοιτος"]):
        grd = Grade()
        grd.id = idx + 1
        grd.name = grd_name
        db.session.add(grd)
    db.session.commit()


def init_database_sqlite():
    app_dir = os.path.realpath(os.path.dirname(__file__))
    database_path = os.path.join(app_dir, app.config['DATABASE_FILE'])
    if not os.path.exists(database_path):
        db.create_all()
        db.session.commit()
        insert_sample_data()


def init_database_postgres():
    existing_tables = db.engine.table_names()
    if 'users' not in existing_tables:
        db.create_all()
        db.session.commit()
        insert_sample_data()


def init_database():
    if 'DATABASE_URL' in os.environ:
        init_database_postgres()
    else:
        init_database_sqlite()


def main():
    app.run(port=5011, debug=True)


# Build a sample db on the fly, if one does not exist yet.
init_database()
# Start app
init_login()

if __name__ == '__main__':
    main()
