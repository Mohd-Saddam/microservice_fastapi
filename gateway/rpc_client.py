import pika
import uuid
import json
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
RABBITMQ_URL = os.environ.get("RABBITMQ_URL")


class OcrRpcClient:
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_URL))
        self.channel = self.connection.channel()

        result = self.channel.queue_declare(queue='', exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True
        )

    def on_response(self, ch, method, properties, body):
        if self.corr_id == properties.correlation_id:
            self.response = body

    def call(self, image_data):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
            exchange = '',
            routing_key = 'ocr_service',
            properties = pika.BasicProperties(
                reply_to = self.callback_queue,
                correlation_id = self.corr_id,
            ),
            body = json.dumps({'image_data': image_data})
        )
        while self.response is None:
            self.connection.process_data_events()
        return json.loads(self.response)