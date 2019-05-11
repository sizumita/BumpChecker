import aiosqlite

database_name = "bumpchecker.db"  # データベース名
table_create_sql = """
create table if not exists bump(
    user_id int,
    bump_datetime int,
    near float
);
"""


async def create_table():
    """"テービルが作成されていない場合作る"""
    async with aiosqlite.connect(database_name) as db:
        await db.execute(table_create_sql)
        await db.commit()


async def create_new_bump_data(user_id, bump_datetime, near):
    async with aiosqlite.connect(database_name) as db:
        await db.execute('insert into bump values(?, ?, ?)', (user_id, bump_datetime.timestamp(), near))
        await db.commit()
    return True


async def get_all_bump_data():
    user_data = {}
    async with aiosqlite.connect(database_name) as db:
        async with db.execute('SELECT * FROM bump') as cursor:
            async for row in cursor:
                if not row[0] in user_data.keys():
                    user_data[row[0]] = dict(count=0, nears=[])
                user_data[row[0]]['count'] += 1
                user_data[row[0]]['nears'].append(row[2])
    return user_data


async def get_range_bump_data_(before, after):
    user_data = {}
    async with aiosqlite.connect(database_name) as db:
        async with db.execute('SELECT * FROM bump where ? < bump_datetime and ? > bump_datetime', (before.timestamp(), after.timestamp())) as cursor:
            async for row in cursor:
                if not row[0] in user_data.keys():
                    user_data[row[0]] = dict(count=0, nears=[])
                user_data[row[0]]['count'] += 1
                user_data[row[0]]['nears'].append(row[2])
    return user_data


async def drop_all_data():
    async with aiosqlite.connect(database_name) as db:
        await db.execute('drop table bump')
        await db.commit()
    await create_table()


async def test():
    import datetime
    import random
    await create_table()
    year_before = datetime.datetime.now() - datetime.timedelta(days=365)
    for x in range(365 * 12):
        await create_new_bump_data(212513828641046529, year_before, random.random())
        year_before += datetime.timedelta(hours=2)


if __name__ == '__main__':
    import asyncio
    # asyncio.get_event_loop().run_until_complete(test())
    asyncio.get_event_loop().run_until_complete(drop_all_data())
