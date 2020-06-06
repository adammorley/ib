#!/usr/bin/python3.7

import asyncio
import time

async def count():
    for i in range(0, 10):
        print('bg job running')
        await asyncio.sleep(1)

async def foo():
    await asyncio.gather(count(), count())

print('hello')
asyncio.run(foo())
print('world')
