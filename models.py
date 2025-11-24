from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class File(db.Model):
    __tablename__ = 'files'
    id = db.Column(db.Integer, primary_key=True)
    drive_id = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(255))
    is_folder = db.Column(db.Boolean, default=False)
    parent_id = db.Column(db.String(255), nullable=True)
    root_key = db.Column(db.String(100), nullable=False)  # ← dari ROOT_FOLDERS
    path = db.Column(db.Text)
    size = db.Column(db.BigInteger)
    web_view_link = db.Column(db.Text)
    modified_time = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)