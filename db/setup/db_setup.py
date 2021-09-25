import asyncio

import asyncpg

from cfg import DB_CREDENTIALS


async def main():
    pdb = await asyncpg.create_pool(**DB_CREDENTIALS)
    with open("db.sql", "r") as f:
        file = f.read()

    await pdb.execute(file)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
