from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_ckeditor import CKEditor

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = r'C:\Users\Lenovo\Documents\SOFT_PROJECT\db_backend\uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
app.config['SECRET_KEY'] = 'my_secret_key'  
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///research_portal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['CKEDITOR_PKG_TYPE'] = 'full'  # Includes all toolbar options

db = SQLAlchemy(app)
ckeditor = CKEditor(app)

from db_backend import routes