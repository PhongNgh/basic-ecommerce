import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "aSgQwIfN0d")
    MONGO_URI = "mongodb+srv://test:12341234@cluster0.i3vkq.mongodb.net/ecommerce?retryWrites=true&w=majority&appName=Cluster0"
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "hOfrkNASyPMHArsIIMretH27L65PdKS8")
    CACHE_TYPE = "RedisCache"
    CACHE_REDIS_HOST = "localhost"
    CACHE_REDIS_PORT = 6379
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_ACCESS_COOKIE_NAME = "access_token_cookie"
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_CSRF_PROTECT = False
    JWT_SESSION_COOKIE = True
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=30)
