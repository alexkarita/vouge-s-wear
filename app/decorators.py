from functools import wraps
from flask import abort
from flask_login import current_user

def admin_required(f):
    """
    Custom decorator to protect admin routes.
    Ensures the user is logged in AND has the is_admin flag set to True.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. Check if the user is even logged in
        # 2. Check if the user's database record has is_admin = True
        if not current_user.is_authenticated or not current_user.is_admin:
            # If either check fails, return a 403 Forbidden error
            abort(403)
            
        return f(*args, **kwargs)
        
    return decorated_function