"""
RabbitMQ publisher – publishes parsed logs to the 'logs.raw' topic exchange.
"""

import json
import logging
from typing import Dict, Any

import aio_pika

logger = logging.getLogger("ingestion.rabbitmq")


class RabbitMQPublisher:
    """Async RabbitMQ publisher using aio-pika."""

    def __init__(self, host: str, user: str, password: str, port: int = 5672):
        self._url = f"amqp://{user}:{password}@{host}:{port}/"
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.Channel | None = None
        self._exchange: aio_pika.Exchange | None = None

    @property
    def connected(self) -> bool:
        return self._connection is not None and not self._connection.is_closed

    async def connect(self):
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        # Declare a durable topic exchange
        self._exchange = await self._channel.declare_exchange(
            "logs.raw",
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )
        logger.info("RabbitMQ publisher connected (exchange=logs.raw)")

    async def publish_log(self, log_data: Dict[str, Any]):
        """Publish a parsed log dict to RabbitMQ."""
        if not self._exchange:
            raise RuntimeError("RabbitMQ not connected")

        routing_key = f"log.{log_data['severity']}.{log_data['service']}"

        message = aio_pika.Message(
            body=json.dumps(log_data).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json",
        )

        await self._exchange.publish(message, routing_key=routing_key)
        logger.debug(f"Published → {routing_key}")

    async def close(self):
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            logger.info("RabbitMQ connection closed")
