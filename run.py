from flask import Flask
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager
from flask_caching import Cache

app = Flask(__name__)
app.config.from_object("config.Config")

mongo = PyMongo(app)
jwt = JWTManager(app)
cache = Cache(app)

from routes import *

if __name__ == "__main__":
    app.run(debug=True)
