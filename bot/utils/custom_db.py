import asyncpg


class Db_Class(object):
    def __init__(self):
        ...

    async def setup(self, **kwargs):
        self.pool: asyncpg.Pool = await asyncpg.create_pool(**kwargs)

    async def write(self, query, *values):
        connection = await self.pool.acquire()
        async with connection.transaction():
            await self.pool.execute(query, *values)
        await self.pool.release(connection)

    async def read(self, query, *values):
        return await self.pool.fetch(query, *values)
