from run import mongo  # Import mongo từ run.py
from werkzeug.security import generate_password_hash, check_password_hash

class User:
    def __init__(self, full_name, username, password, role="member"):
        self.full_name = full_name
        self.username = username
        self.password = generate_password_hash(password)
        self.role = role

    def save(self):
        mongo.db.users.insert_one({
            "username": self.username,
            "password": self.password,
            "full_name": self.full_name,
            "role": self.role
        })

    @classmethod
    def find_by_username(cls, username):
        return mongo.db.users.find_one({"username": username})

    @classmethod
    def validate_password(cls, stored_password, provided_password):
        return check_password_hash(stored_password, provided_password)

class Product:
    def __init__(self, name, price, quantity, description, image_url):
        self.name = name
        self.price = price
        self.quantity = quantity
        self.description = description
        self.image_url = image_url

    def save(self):
        mongo.db.products.insert_one({
            "name": self.name,
            "price": self.price,
            "quantity": self.quantity,
            "description": self.description,
            "image": self.image_url
        })

    @classmethod
    def find_by_name(cls, name):
        return mongo.db.products.find_one({"name": name})

    @classmethod
    def find_by_id(cls, product_id):
        return mongo.db.products.find_one({"_id": product_id})

    @classmethod
    def update(cls, product_id, updates):
        mongo.db.products.update_one({"_id": product_id}, {"$set": updates})

    @classmethod
    def delete(cls, product_id):
        mongo.db.products.delete_one({"_id": product_id})