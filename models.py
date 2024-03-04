# models.py
from . import db

class OTP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    otp = db.Column(db.String(4), nullable=False)
