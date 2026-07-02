from collections import defaultdict
from time import time

class InMemoryRateLimiter:
    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.buckets = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time()
        bucket = self.buckets[key]
        bucket[:] = [t for t in bucket if now - t < self.window]
        if len(bucket) >= self.max_requests:
            return False
        bucket.append(now)
        return True

login_limiter = InMemoryRateLimiter(max_requests=10, window_seconds=60)
register_limiter = InMemoryRateLimiter(max_requests=5, window_seconds=300)

