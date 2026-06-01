# Import asyncio: Python's built-in library that runs async code (the "event loop").
import asyncio

# Import aiohttp: a library for making async (non-blocking) HTTP requests.
import aiohttp


# "async def" makes this a coroutine - a special function that can use "await".
async def fetch_example():
    # The API endpoint we want to fetch (info about Python's cpython repo).
    url = "https://api.github.com/repos/python/cpython"

    # Open a ClientSession - think of it like opening a browser tab to send requests.
    # "async with" auto-closes the session when we're done (no memory leak).
    async with aiohttp.ClientSession() as session:
        # Send a GET request to the URL. "await" pauses here while data travels
        # over the network, letting other work run in the meantime.
        async with session.get(url) as response:
            # Convert the response body (JSON text) into a Python dictionary.
            # "await" again because reading the body is also a wait-y operation.
            data = await response.json()

            # data is a dict; data["name"] is the repo's name -> "cpython".
            print(f"Fetched: {data['name']}")


# asyncio.run(...) starts the event loop and runs our coroutine to completion.
# This must be OUTSIDE the function (no indentation), at the bottom of the file.
asyncio.run(fetch_example())
