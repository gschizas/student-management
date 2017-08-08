import os

from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

app = Flask(__name__)
app.secret_key = b'\xda~z\xd3Y\x84\xe9vl\xa8\x01\xc8F\xd0\x98\xa2\x8e\xb4\xc2\x00\x18w\xff\xe0'
app.config['DATABASE_FILE'] = 'studentmanagement.sqlite'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + app.config['DATABASE_FILE']
app.config['SQLALCHEMY_ECHO'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Year(db.Model):
    __tablename__ = 'years'
    id = db.Column(db.Integer, primary_key=True)
    year_start = db.Column(db.Integer)
    year_end = db.Column(db.Integer)

    def __str__(self):
        return f"{self.year_start}-{self.year_end}"


class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(30))
    last_name = db.Column(db.String(50))
    current_fee = db.Column(db.DECIMAL)
    year_id = db.Column(db.Integer, ForeignKey('years.id'))
    year = relationship('Year')

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


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


# Flask and Flask-SQLAlchemy initialization here

admin = Admin(app, url='', name='studentmanagement', template_mode='bootstrap3')
admin.add_view(ModelView(Student, db.session, name="Μαθητές"))
admin.add_view(ModelView(Lesson, db.session, name="Μαθήματα"))
admin.add_view(ModelView(Payment, db.session, name="Πληρωμές"))
admin.add_view(ModelView(Year, db.session, name="Έτη"))

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
