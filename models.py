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
        """Kiểm tra mật khẩu"""
        return check_password_hash(stored_password, provided_password)