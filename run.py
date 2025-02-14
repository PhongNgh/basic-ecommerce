from flask import Flask
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager
from flask_caching import Cache
from config import Config
import cloudinary

app = Flask(__name__)
app.config.from_object(Config)

mongo = PyMongo(app)
jwt = JWTManager(app)
cache = Cache(app)

cloudinary.config(
    cloud_name=app.config["CLOUDINARY_CLOUD_NAME"],
    api_key=app.config["CLOUDINARY_API_KEY"],
    api_secret=app.config["CLOUDINARY_API_SECRET"]
)

from routes import *  # Import routes sau khi khởi tạo mongo

if __name__ == "__main__":
    app.run(debug=True)
