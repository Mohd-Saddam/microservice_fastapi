# FastAPI Microservice Demo

This repository contains a simple microservices demo built with FastAPI and RabbitMQ. It showcases four services working together:

- Gateway Service: Entry point for clients. Proxies Auth endpoints and exposes an OCR endpoint that talks to the ML service via RabbitMQ RPC.
- ML Service: Processes images with OCR and publishes notifications.
- Auth Service: User registration, login (JWT), OTP generation/verification, and email verification state.
- Notification Service: Listens on RabbitMQ and sends emails when requested.

The services communicate primarily through HTTP (Gateway ↔ Auth) and RabbitMQ (Gateway ↔ ML, ML/Auth → Notification).


## Architecture Diagram


<img width="1920" height="1080" alt="image1" src="https://github.com/user-attachments/assets/675f56ce-b4a3-4469-a008-dcde1f067b6b" />





- Client → Gateway (HTTP)
- Gateway → Auth (HTTP)
- Gateway → ML (RabbitMQ RPC)
- ML → Notification (RabbitMQ queue)
- Auth → Notification (RabbitMQ queue for OTP emails)

Ports used by default:
- Auth Service: 5000
- Gateway Service: 5001


## Prerequisites

- Windows, macOS, or Linux
- Python 3.11.8
- Docker Desktop (for Postgres and RabbitMQ)

Optional but recommended:
- A virtual environment tool such as venv or conda
- cURL or an API client (e.g., Postman)


## Quick Start

1) Start Postgres (Docker)

Run this once to create and start a local Postgres container:

- Windows PowerShell / macOS / Linux:
  docker run --name postgres-db -e POSTGRES_PASSWORD=12 -d -p 5432:5432 postgres

2) Start RabbitMQ (Docker)

- Windows PowerShell / macOS / Linux:
  docker run -it --rm --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3.13-management

RabbitMQ management UI will be available at http://localhost:15672 (default creds: guest / guest).

3) Clone the repository

  git clone https://github.com/Mohd-Saddam/microservice_fastapi.git
  cd microservice_fastapi

This README assumes the project root is the microservice_project folder.


## Environment Variables

Create .env files where needed. The following variables are used by the code:

Common
- RABBITMQ_URL=localhost

Gateway Service
- JWT_SECRET=some-long-random-secret
- AUTH_BASE_URL=http://localhost:5000
- RABBITMQ_URL=localhost

Auth Service
- POSTGRES_HOST=localhost
- POSTGRES_DB=postgres
- POSTGRES_USER=postgres
- POSTGRES_PASSWORD=12
- (Optional) JWT secret/expiry handled internally; keep consistent with Gateway JWT_SECRET if sharing

ML Service
- RABBITMQ_URL=localhost

Notification Service
- RABBITMQ_URL=localhost

Place the .env files as follows:
- microservice_project/gateway/.env
- microservice_project/auth/.env
- microservice_project/ml_services/.env
- microservice_project/notification_service/.env


## Install Dependencies and Run

Important:
- Use Python 3.11.8
- Create a virtual environment per service and install that service’s requirements.txt

Below are Windows PowerShell examples. On macOS/Linux, replace backslashes with slashes and activate venv appropriately.

### 1) Auth Service (port 5000)

- Path: microservice_project/auth
- Entry point: main.py

Steps:
1. Create and activate a virtual environment
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

2. Install dependencies
   pip install -r requirements.txt

3. Ensure .env has Postgres settings (see Environment Variables section).

4. Run the service
   python main.py

You should see FastAPI running on http://0.0.0.0:5000

Health check:
- GET http://localhost:5000/check_api


### 2) Gateway Service (port 5001)

- Path: microservice_project/gateway
- Entry point: main.py

Steps:
1. Create and activate a virtual environment
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

2. Install dependencies
   pip install -r requirements.txt

3. Ensure gateway/.env has JWT_SECRET, AUTH_BASE_URL, RABBITMQ_URL.

4. Run the service
   python main.py

The Gateway connects to RabbitMQ queues gatewayservice and ocr_service on startup.


### 3) ML Service (worker)

- Path: microservice_project/ml_services
- Entry point: main.py

Steps:
1. Create and activate a virtual environment
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

2. Install dependencies
   pip install -r requirements.txt

3. Ensure ml_services/.env has RABBITMQ_URL.

4. Run the worker
   python main.py

You should see: " [x] Awaiting RPC requests"


### 4) Notification Service (worker)

- Path: microservice_project/notification_service
- Entry point: main.py

Steps:
1. Create and activate a virtual environment
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

2. Install dependencies
   pip install -r requirements.txt

3. Ensure notification_service/.env has RABBITMQ_URL.

4. Run the worker
   python main.py

It will start consuming messages from the email_notification queue.


## Using the API

1) Register a user (via Gateway → Auth)

POST http://localhost:5001/auth/register
Body (JSON):
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "password": "StrongPass123"
}

Expected: 201 with a message to verify email.

2) Generate OTP (via Gateway → Auth)

POST http://localhost:5001/auth/generate_otp
Body (JSON):
{
  "email": "jane@example.com"
}

Auth service will place a message on RabbitMQ for the Notification service to send an email. For demo purposes, check the Notification logs/output.

3) Verify OTP (via Gateway → Auth)

POST http://localhost:5001/auth/verify_otp
Body (JSON):
{
  "email": "jane@example.com",
  "otp": 123456
}

4) Login to get JWT (via Gateway → Auth)

POST http://localhost:5001/auth/login
Body (JSON):
{
  "username": "jane@example.com",
  "password": "StrongPass123"
}

Copy the access token from the response.

5) OCR endpoint (via Gateway → ML over RabbitMQ)

POST http://localhost:5001/ocr
Headers:
- Authorization: Bearer <your_jwt_token>

Form-data:
- file: <upload an image file>

Gateway will:
- Save the file temporarily
- Send base64 image payload to ML through RabbitMQ RPC
- Receive OCR text
- Delete temp file and return the response


## Troubleshooting

- Postgres connection issues (Auth)
  - Ensure the Docker Postgres container is running: docker ps
  - Verify .env values in auth/.env match the container: host=localhost, db=postgres, user=postgres, password=12
  - If using a different DB or credentials, update auth/.env accordingly

- RabbitMQ connection issues
  - Ensure the RabbitMQ container is running and RABBITMQ_URL=localhost is set in each service .env
  - Access http://localhost:15672 to confirm queues: ocr_service, email_notification

- Port conflicts
  - If 5000/5001 are in use, either stop the conflicting service or adjust uvicorn run ports in the corresponding main.py files

- Python version
  - Use Python 3.11.8 as the dependencies are tested with this version


## Development Notes

- The Auth service uses SQLAlchemy and expects a running Postgres. Tables are created on startup.
- The Gateway relies on JWT_SECRET to validate tokens returned by Auth. Ensure both sides use the same secret where intended.
- The ML service references OCR utilities (keras-ocr in utils). Ensure system dependencies (e.g., Tesseract or C++ build tools) are installed if required by your OCR backend.
- The Notification service consumes the email_notification queue and delegates to email_service.notification(body).
- Logging is done via print statements for simplicity. Consider integrating a logging framework for production use.
