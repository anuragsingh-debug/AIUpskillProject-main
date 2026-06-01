"""Simple rate limiting."""

import asyncio


# WHY this class exists:
# When we fire many requests at once (e.g. 30 HN stories together), hitting a
# server with ALL of them can get us blocked, or overwhelm our own network.
# Think of an ATM with only 2 machines: a guard lets only 2 people in at a time,
# the rest wait in line. This class is that guard — "max N tasks at a time".
class RateLimiter:
    """
    Simple semaphore-based rate limiter.

    Limits concurrent operations.
    """

    # Set up the "guard". Semaphore(N) = N entry tokens / N slots available.
    # Each task must grab a token to run; when tokens run out, others wait.
    def __init__(self, max_concurrent: int = 10):
        """
        Initialize rate limiter.

        Args:
            max_concurrent: Maximum concurrent operations
        """
        self.semaphore = asyncio.Semaphore(max_concurrent)

    # Runs at the START of `async with limiter:` — "enter the ATM".
    # acquire() takes one token; if none are free, it WAITS here until one frees up.
    async def __aenter__(self):
        """Acquire semaphore."""
        await self.semaphore.acquire()
        return self

    # Runs at the END of the `async with` block — "leave the ATM".
    # release() gives the token back so a waiting task can now enter.
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release semaphore."""
        self.semaphore.release()

    # Helper: run any coroutine WITH the limit applied automatically.
    # `async with self` grabs a token, runs the work, then frees the token.
    async def execute(self, coro):
        """
        Execute coroutine with rate limiting.

        Args:
            coro: Coroutine to execute

        Returns:
            Result of coroutine
        """
        async with self:
            return await coro


# Test it
async def test_rate_limiter():
    """Test rate limiter."""
    import time

    limiter = RateLimiter(max_concurrent=2)

    async def slow_task(n):
        """Simulated slow task."""
        async with limiter:
            print(f"  Task {n} starting")
            await asyncio.sleep(0.5)
            print(f"  Task {n} done")
            return n

    print("Testing with max_concurrent=2...")
    start = time.time()

    # Run 4 tasks - should take ~1 second (2 at a time)
    await asyncio.gather(*[slow_task(i) for i in range(4)])

    elapsed = time.time() - start
    print(f"\n✅ Completed in {elapsed:.2f}s")
    print("   (Should be ~1.0s with 2 concurrent)")


if __name__ == "__main__":
    asyncio.run(test_rate_limiter())
