from flask import redirect, url_for, flash
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
import json
from functools import wraps

def role_required(role):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            try:
                verify_jwt_in_request(locations=["cookies"])
                current_user = json.loads(get_jwt_identity())
                if current_user["role"] != role:
                    flash("Unauthorized access", "danger")
                    return redirect(url_for("login"))
            except Exception:
                flash("Session expired or unauthorized access", "danger")
                return redirect(url_for("login"))
            return fn(*args, **kwargs)
        return decorator
    return wrapper

def log_request():
    from flask import request
    print(f"Request: {request.method} {request.path}")