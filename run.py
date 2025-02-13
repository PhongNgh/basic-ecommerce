from flask import Flask
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager
from flask_caching import Cache
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

mongo = PyMongo(app)
jwt = JWTManager(app)
cache = Cache(app)

from routes import *  # Import routes sau khi khởi tạo mongo

if __name__ == "__main__":
    app.run(debug=True)
