import logging
import os
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

logger = logging.getLogger(__name__)

_security = HTTPBasic()


def get_current_user(credentials: HTTPBasicCredentials = Depends(_security)) -> str:
    """Gate a route behind a single hardcoded username/password pair.

    Unset env vars compare against empty strings, so an unconfigured deploy
    fails closed (locked out) rather than open.
    """
    valid_username = secrets.compare_digest(
        credentials.username, os.getenv("BASIC_AUTH_USERNAME", "")
    )
    valid_password = secrets.compare_digest(
        credentials.password, os.getenv("BASIC_AUTH_PASSWORD", "")
    )
    if not (valid_username and valid_password):
        logger.warning("Failed Basic Auth attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
