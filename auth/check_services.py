"""
Service Health Check Script
Checks if PostgreSQL and RabbitMQ are running before starting the auth service.
"""
import psycopg2
import pika
import os
from dotenv import load_dotenv

load_dotenv()

def check_postgresql():
    """Check if PostgreSQL is accessible"""
    try:
        postgres_host = os.environ.get("POSTGRES_HOST")
        postgres_db = os.environ.get("POSTGRES_DB")
        postgres_user = os.environ.get("POSTGRES_USER")
        postgres_password = os.environ.get("POSTGRES_PASSWORD")

        conn = psycopg2.connect(
            host=postgres_host,
            database=postgres_db,
            user=postgres_user,
            password=postgres_password
        )
        conn.close()
        print("✅ PostgreSQL is running and accessible")
        return True
    except psycopg2.OperationalError as e:
        print(f"❌ PostgreSQL is NOT accessible: {e}")
        print("   Please start PostgreSQL service")
        return False

def check_rabbitmq():
    """Check if RabbitMQ is accessible"""
    try:
        rabbitmq_host = os.environ.get("RABBITMQ_URL", "localhost")
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=rabbitmq_host)
        )
        connection.close()
        print("✅ RabbitMQ is running and accessible")
        return True
    except Exception as e:
        print(f"❌ RabbitMQ is NOT accessible: {e}")
        print("   Please start RabbitMQ service")
        return False

if __name__ == "__main__":
    print("\n=== Checking External Services ===\n")

    postgres_ok = check_postgresql()
    rabbitmq_ok = check_rabbitmq()

    print("\n=== Summary ===")
    if postgres_ok and rabbitmq_ok:
        print("✅ All services are running. You can start the auth service.")
    else:
        print("⚠️  Some services are not available.")
        print("   The auth service will start but may have limited functionality.")
        print("   Database-dependent endpoints will return 503 errors.")
