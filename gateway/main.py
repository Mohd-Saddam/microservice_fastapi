from fastapi import FastAPI, HTTPException ,  File, UploadFile
import fastapi as _fastapi
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
from jwt.exceptions import DecodeError
from pydantic import BaseModel
import requests
import base64
import pika
import logging
import os
import jwt
import rpc_client
from contextlib import asynccontextmanager

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Load environment variables from .env file
load_dotenv()
logging.basicConfig(level=logging.INFO)

# Retrieve environment variables
JWT_SECRET = os.getenv("JWT_SECRET")
AUTH_BASE_URL = os.getenv("AUTH_BASE_URL")
RABBITMQ_HOST = os.getenv("RABBITMQ_URL")

# Defer RabbitMQ connection to startup
connection = None
channel = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global connection, channel
    # Try to connect to RabbitMQ
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()
        channel.queue_declare(queue='gatewayservice')
        channel.queue_declare(queue='ocr_service')
        logging.info("Connected to RabbitMQ and declared queues")
    except Exception as e:
        logging.error(f"Failed to connect to RabbitMQ: {e}")
    yield

app = FastAPI(lifespan=lifespan)

# JWT token validation
async def jwt_validation(token: str = _fastapi.Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except DecodeError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Pydantic model for request body
class GenerateUserTokenRequest(BaseModel):
    username: str
    password: str

class UserCredentials(BaseModel):
    username: str
    password: str

class UserRegistration(BaseModel):
    name: str
    email: str
    password: str

class GenerateOtp(BaseModel):
    email: str

class VerifyOtp(BaseModel):
    email: str
    otp: int


# Authentication service route
@app.post("/auth/login", tags=["Authentication Service"])
async def login(user_data: UserCredentials):
    try:
        response = requests.post(f"{AUTH_BASE_URL}/api/token", json = {"username": user_data.username, "password": user_data.password})
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.json())
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Authentication service is unavailable")

    except Exception as e:
        logging.error(f"Error during login: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/auth/register", tags=['Authentication Service'])
async def registration(user_data:UserRegistration):
    try:
        print(AUTH_BASE_URL)
        response = requests.post(f"{AUTH_BASE_URL}/api/users", json = {"name": user_data.name, "email": user_data.email, "password": user_data.password})
        if response.status_code == 201:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.json())
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Authentication service is unavailable")

    except Exception as e:
        logging.error(f"Error during registration: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/auth/generate_otp", tags=['Authentication Service'])
async def generate_otp(user_data:GenerateOtp):
    try:
        response = requests.post(f"{AUTH_BASE_URL}/api/users/generate_otp", json = {"email": user_data.email})
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.json())
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Authentication service is unavailable")

    except Exception as e:
        logging.error(f"Error during OTP generation: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/auth/verify_otp", tags=['Authentication Service'])
async def verify_otp(user_data:VerifyOtp):
    try:
        response = requests.post(f"{AUTH_BASE_URL}/api/users/verify_otp", json={"email":user_data.email ,"otp":user_data.otp})
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.json())
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Authentication service is unavailable")
    except Exception as e:
        logging.error(f"Error during OTP verification: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")



# ml microservice route - OCR route
@app.post('/ocr' ,  tags=['Machine learning Service'] )
def ocr(file: UploadFile = File(...),
        payload: dict = _fastapi.Depends(jwt_validation)):
    # Save the uploaded file to a temporary location
    with open(file.filename, "wb") as buffer:
        buffer.write(file.file.read())

    ocr_rpc = rpc_client.OcrRpcClient()

    with open(file.filename, "rb") as buffer:
        file_data = buffer.read()
        file_base64 = base64.b64encode(file_data).decode()

    request_json = {
        'user_name': payload['name'],
        'user_email': payload['email'],
        'user_id': payload['id'],
        'file': file_base64
    }

    # Call the OCR microservice with the request JSON
    response = ocr_rpc.call(request_json)

    # Delete the temporary image file
    os.remove(file.filename)
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5001, reload=True)
