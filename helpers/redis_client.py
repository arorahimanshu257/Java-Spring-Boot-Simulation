import redis
from helpers.logger_config import logger
from redis.retry import Retry
from redis.exceptions import (TimeoutError, ConnectionError)
from redis.backoff import ExponentialBackoff
import os
import base64


# os.environ["REDIS_HOST"] = "da-api-platform-redis-dev.redis.cache.windows.net"
# os.environ["REDIS_PORT"] = "6380"
# os.environ["REDIS_PASSWORD"] = "TXBYQTlJVTF3QzlpRXRab2xTN3RaaUdQUlVCenhIMzYxQXpDYVAzUVBZaz0="
# os.environ["REDIS_SSL"] = "True"

class RedisClientSingleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(RedisClientSingleton, cls).__new__(cls)
            cls._instance._initialize(*args, **kwargs)
        return cls._instance

    def _initialize(self):
        logger.info('---------------- Redis Configuration ---------------- ')

        redis_host = os.environ["REDIS_HOST"]
        redis_port = os.environ["REDIS_PORT"]
        redis_password = os.environ["REDIS_PASSWORD"]

        # Decode the Base64 string
        decoded_password = base64.b64decode(redis_password).decode('utf-8')
        sslValue = os.getenv('REDIS_SSL')

        sslBool = sslValue.lower() == 'true'
        logger.info('REDIS sslValue is %s and sslBool is %s and type is %s', sslValue, sslBool, type(sslBool))

        try:

            self.redisClient = redis.StrictRedis(
                host=redis_host,
                port=int(redis_port),
                password=decoded_password,
                ssl=sslBool,  # SSL is required for Azure Cache for Redis
                decode_responses=True,  # Decode responses as UTF-8 strings
                retry=Retry(ExponentialBackoff(cap=10, base=1), 7),
                retry_on_error=[ConnectionError, TimeoutError],
                health_check_interval=1
            )

        except redis.ConnectionError as e:
            if self.redisClient:
                self.redisClient.close()
                logger.info("Closed Redis connection.")
            logger.error(f"Could not connect to Redis: {e}")
            raise Exception(f"Could not connect to Redis: {e}")

    def get_client(self):
        return self.redisClient

# Usage

logger.debug("Redis client being initialized")

redis_client_singleton = RedisClientSingleton() if os.getenv("ENABLE_LOGSTREAMING") else None

redis_client = redis_client_singleton.get_client() if redis_client_singleton else None
