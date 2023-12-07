import asyncio
import functools


def wait_tasks(fn):
    @functools.wraps(fn)
    async def inner(*args, **kwargs):
        result = await fn(*args, **kwargs)
        while set(filter(lambda t: not t is asyncio.current_task(), asyncio.all_tasks())):
            await asyncio.sleep(0)
        return result
    return inner


