# ============================================================
# AUTHENTICATION
# backend/app/auth.py
# ============================================================

import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv
from jose import jwt
from passlib.context import CryptContext


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

AUTH_DB = BASE_DIR / "data" / "users.db"

AUTH_DB.parent.mkdir(
    parents=True,
    exist_ok=True,
)

SECRET_KEY = os.getenv(
    "AUTH_SECRET_KEY",
    "enterprise-ai-demo-secret-change-this"
)

ALGORITHM = "HS256"

TOKEN_EXPIRE_HOURS = 24


pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto",
)


# ============================================================
# DATABASE
# ============================================================

def get_connection():

    connection = sqlite3.connect(
        AUTH_DB
    )

    connection.row_factory = sqlite3.Row

    return connection


def init_auth_db():

    connection = get_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    connection.commit()

    connection.close()


# ============================================================
# PASSWORD
# ============================================================

def hash_password(password: str):

    return pwd_context.hash(
        password
    )


def verify_password(
    password: str,
    password_hash: str,
):

    return pwd_context.verify(
        password,
        password_hash,
    )


# ============================================================
# USERS
# ============================================================

def create_user(
    name: str,
    email: str,
    password: str,
):

    email = email.lower().strip()

    connection = get_connection()

    try:

        password_hash = hash_password(
            password
        )

        cursor = connection.execute(
            """
            INSERT INTO users
            (
                name,
                email,
                password_hash,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                name.strip(),
                email,
                password_hash,
                datetime.now(
                    timezone.utc
                ).isoformat(),
            ),
        )

        connection.commit()

        user_id = cursor.lastrowid

        return {
            "id": user_id,
            "name": name.strip(),
            "email": email,
        }

    finally:

        connection.close()


def get_user_by_email(
    email: str,
):

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (
                email.lower().strip(),
            ),
        ).fetchone()

        if not row:
            return None

        return dict(row)

    finally:

        connection.close()


# ============================================================
# JWT
# ============================================================

def create_access_token(
    user_id: int,
    email: str,
):

    expires = datetime.now(
        timezone.utc
    ) + timedelta(
        hours=TOKEN_EXPIRE_HOURS
    )

    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expires,
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_access_token(
    token: str,
):

    try:

        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

    except Exception:

        return None