import time
from collections import deque
from .config import FREE_TIER_REQUESTS_PER_MIN


class RateLimiter:
    def __init__(self, max_requests_per_minute: int = FREE_TIER_REQUESTS_PER_MIN):
        self.max_rpm = max_requests_per_minute
        self.timestamps: deque[float] = deque()

    def wait_if_needed(self) -> float:
        """Block until it's safe to make another request.

        Returns the number of seconds waited (0 if no wait was needed).
        """
        now = time.time()
        # Remove timestamps older than 60 seconds
        while self.timestamps and self.timestamps[0] < now - 60:
            self.timestamps.popleft()

        waited = 0.0
        if len(self.timestamps) >= self.max_rpm:
            sleep_time = 60 - (now - self.timestamps[0]) + 0.5
            if sleep_time > 0:
                waited = sleep_time
                time.sleep(sleep_time)

        self.timestamps.append(time.time())
        return waited


# Shared instance for all Cerebras API calls
cerebras_rate_limiter = RateLimiter()
