import json
from datetime import timedelta
import redis
from redis import Redis
import random

redis = Redis(host="localhost", port=6379, decode_responses=True)

def cache_get_json(key: str):
    data = redis.get(key)
    return json.loads(data) if data else None

def cache_set_json(key: str, value, ttl: int):
    jitter = random.randint(0, 10)
    redis.setex(key, timedelta(seconds=ttl + jitter), json.dumps(value))

def invalidate(*keys):
    if keys:
        redis.delete(*keys)

def invalidate_pattern(pattern: str):
    for key in redis.scan_iter(pattern):
        redis.delete(key)