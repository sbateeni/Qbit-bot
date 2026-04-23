from typing import Dict

from fastapi import Header


def get_current_user(authorization: str = Header(default="")) -> Dict:
    """
    Local single-user auth mode:
    - If bearer token exists, use it as a stable local user id.
    - Otherwise fallback to a local default user.
    """
    user_id = "local-user"
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        if token:
            user_id = token
    return {"id": user_id, "email": "local@qbit"}
