from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(35), nullable=False)
    last_name = db.Column(db.String(35), nullable=False)
    username = db.Column(db.String(35), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(128), nullable=False)

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


class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(30), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    current_fee = db.Column(db.DECIMAL, nullable=False)
    year_start = db.Column(db.Integer, nullable=False)
    location = db.Column(db.SmallInteger, nullable=True)
    subject = db.Column(db.SmallInteger, nullable=True)
    grade = db.Column(db.SmallInteger, nullable=True)
    notes = db.Column(db.Text, nullable=True)


    @property
    def display_name(self):
        return f'{self.first_name} {self.last_name}'

    @property
    def display_year(self):
        return f'{self.year_start}-{(self.year_start+1) % 100}'

    def __str__(self):
        return f'{self.display_name} ({self.display_year})'


class Lesson(db.Model):
    __tablename__ = 'lessons'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, ForeignKey('students.id'), nullable=False)
    student = relationship('Student')
    date = db.Column(db.Date, nullable=False)
    hours = db.Column(db.Integer, nullable=False)
    fee = db.Column(db.DECIMAL)

    def __str__(self):
        return f'{self.student} - {self.date} ({self.hours})'


class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, ForeignKey('students.id'), nullable=False)
    student = relationship('Student')
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.DECIMAL, nullable=False)
