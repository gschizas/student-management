from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

db = SQLAlchemy()


class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(30))
    last_name = db.Column(db.String(50))
    current_fee = db.Column(db.DECIMAL)


class Lesson(db.Model):
    __tablename__ = 'lessons'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, ForeignKey('students.id'))
    student = relationship('Student')
    date = db.Column(db.Date)
    hours = db.Column(db.Integer)
    fee = db.Column(db.DECIMAL)


class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, ForeignKey('students.id'))
    student = relationship('Student')
    date = db.Column(db.Date)
    amount = db.Column(db.DECIMAL)
