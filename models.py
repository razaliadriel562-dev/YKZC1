from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    major = db.Column(db.String(50))
    grade = db.Column(db.String(10))
    class_name = db.Column(db.String(20))
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    stock = db.Column(db.Integer, default=0)
    logs = db.relationship('InventoryLog', backref='material', lazy=True)

class InventoryLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    material_id = db.Column(db.Integer, db.ForeignKey('material.id'))
    amount = db.Column(db.Integer, nullable=False)
    purpose = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    user = db.relationship('User', backref='logs')

class CompetitionRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    competition_name = db.Column(db.String(100), nullable=False)
    award = db.Column(db.String(50))
    date = db.Column(db.Date)
    is_team = db.Column(db.Boolean, default=False)
    teammates = db.Column(db.String(200))
    certificate_path = db.Column(db.String(200))
    materials_path = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.now)
    user = db.relationship('User', backref='competitions')

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)