import jwt
import sqlalchemy.orm as _orm
import sqlalchemy.exc as _sa_exc
import passlib.hash as _hash
import email_validator as _email_check
import fastapi as _fastapi
import fastapi.security as _security
from passlib.hash import bcrypt
import database as _database
import schemas as _schemas
import models as _models
import random
import json
import pika
import time
import os
import hashlib


class DatabaseUnavailable(Exception):
    pass


# Load environment variables
JWT_SECRET = os.getenv("JWT_SECRET")
RABBITMQ_URL = os.getenv("RABBITMQ_URL")
oauth2schema = _security.OAuth2PasswordBearer("/api/token")


def _prepare_password(password: str) -> str:
    """
    Prepare password for bcrypt hashing.
    Bcrypt has a 72-byte limit, so we pre-hash long passwords with SHA256.
    """
    if len(password.encode('utf-8')) > 72:
        # For long passwords, use SHA256 hash to reduce to fixed size
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    return password


def create_database():
    # Create database tables
    return _database.Base.metadata.create_all(bind=_database.engine)


def get_db():
    # Dependency to get a database session
    db = _database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_user_by_email(email: str, db: _orm.Session):
    # Retrieve a user by email from the database
    try:
        return db.query(_models.User).filter(_models.User.email == email and _models.User.is_verified == True).first()
    except _sa_exc.OperationalError:
        raise DatabaseUnavailable("Database is unavailable")


async def create_user(user: _schemas.UserCreate, db: _orm.Session):
    # Create a new user in the database
    try:
        valid = _email_check.validate_email(user.email)
        name = user.name
        email = valid.email
    except _email_check.EmailNotValidError:
        raise _fastapi.HTTPException(status_code=404, detail="Please enter a valid email")

    try:
        # Prepare password for bcrypt (handles long passwords)
        password_prepared = _prepare_password(user.password)
        hashed_password = _hash.bcrypt.hash(password_prepared)

        user_obj = _models.User(email=email, name=name, hashed_password=hashed_password)
        db.add(user_obj)
        db.commit()
        db.refresh(user_obj)
        return user_obj
    except _sa_exc.OperationalError:
        raise DatabaseUnavailable("Database is unavailable")


async def authenticate_user(email: str, password: str, db: _orm.Session):
    # Authenticate a user
    user = await get_user_by_email(email=email, db=db)

    if not user:
        return False

    if not user.is_verified:
        return 'is_verified_false'

    if not user.verify_password(password):
        return False

    return user


async def create_token(user: _models.User):
    # Create a JWT token for authentication
    user_obj = _schemas.User.from_orm(user)
    user_dict = user_obj.model_dump()
    del user_dict["date_created"]
    token = jwt.encode(user_dict, JWT_SECRET, algorithm="HS256")
    return dict(access_token=token, token_type="bearer")


async def get_current_user(db: _orm.Session = _fastapi.Depends(get_db), token: str = _fastapi.Depends(oauth2schema)):
    # Get the current authenticated user from the JWT token
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        try:
            user = db.query(_models.User).get(payload["id"])
        except _sa_exc.OperationalError:
            raise DatabaseUnavailable("Database is unavailable")
    except:
        raise _fastapi.HTTPException(status_code=401, detail="Invalid Email or Password")
    return _schemas.User.from_orm(user)


def generate_otp():
    # Generate a random OTP
    return str(random.randint(100000, 999999))


def connect_to_rabbitmq():
    # Connect to RabbitMQ
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_URL))
            return connection
        except pika.exceptions.AMQPConnectionError:
            print("Failed to connect to RabbitMQ. Retrying in 5 seconds...")
            time.sleep(5)


def send_otp(email, otp, channel):
    # Send an OTP email notification using RabbitMQ
    connection = connect_to_rabbitmq()
    channel = connection.channel()
    message = {'email': email,
               'subject': 'Account Verification OTP Notification',
               'other': 'null',
               'body': f'Your OTP for account verification is: {otp} \n Please enter this OTP on the verification page to complete your account setup. \n If you did not request this OTP, please ignore this message.\n Thank you '
               }

    try:
        queue_declare_ok = channel.queue_declare(queue='email_notification', passive=True)
        current_durable = queue_declare_ok.method.queue

        if current_durable:
            if queue_declare_ok.method.queue != current_durable:
                channel.queue_delete(queue='email_notification')
                channel.queue_declare(queue='email_notification', durable=True)
        else:
            channel.queue_declare(queue='email_notification', durable=True)

        channel.basic_publish(
            exchange="",
            routing_key='email_notification',
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
            ),
        )
        print("Sent OTP email notification")
    except Exception as err:
        print(f"Failed to publish message: {err}")
    finally:
        channel.close()
        connection.close()
