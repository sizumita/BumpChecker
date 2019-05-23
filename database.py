import aiosqlite
import asyncio 
database_name = "bumpchecker.db"  # データベース名
table_create_sql = """
create table if not exists bump(
    user_id int,
    bump_datetime int,
    near float,
    success int
    );
"""


async def create_table():
    """"テービルが作成されていない場合作る"""
    async with aiosqlite.connect(database_name) as db:
        await db.execute(table_create_sql)
        await db.commit()
        await asyncio.sleep(1)

    # ここからアプデ
    count = await get_column_count()
    if not count:
        return

    if not count == 4:
        async with aiosqlite.connect(database_name) as db:
            await db.execute('alter table bump add column success int default 1;')
            print('successful column update')


async def get_column_count():
    """カラム数の取得"""
    async with aiosqlite.connect(database_name) as db:
        data = await db.execute('select * from bump')
        one = await data.fetchone()
        await data.close()
    if not one:
        return 0
    return len(one)


async def create_new_bump_data(user_id, bump_datetime, near, success):
    async with aiosqlite.connect(database_name) as db:
        # datetimeはtimestampで保存
        await db.execute('insert into bump values(?, ?, ?, ?)', (user_id, bump_datetime.timestamp(), near, success))
        await db.commit()
    return True


async def get_all_bump_data():
    user_data = {}
    async with aiosqlite.connect(database_name) as db:
        async with db.execute('SELECT * FROM bump where success = 1') as cursor:
            async for row in cursor:
                if not row[0] in user_data.keys():
                    user_data[row[0]] = dict(count=0, nears=[])
                user_data[row[0]]['count'] += 1
                user_data[row[0]]['nears'].append(row[2])
    return user_data


async def get_range_bump_data_(before, after):
    user_data = {}
    async with aiosqlite.connect(database_name) as db:
        # datetimeはtimestampで保存されているためtimestampに変換
        async with db.execute('SELECT * FROM bump where ? < bump_datetime and ? > bump_datetime and success = 1',
                              (before.timestamp(), after.timestamp())) as cursor:
            async for row in cursor:
                if not row[0] in user_data.keys():
                    user_data[row[0]] = dict(count=0, nears=[])
                user_data[row[0]]['count'] += 1
                user_data[row[0]]['nears'].append(row[2])
    return user_data


async def check_data(user_id, bump_datetime):
    """ユーザーidと時間で、すでに追加されていないかチェックする"""
    async with aiosqlite.connect(database_name) as db:
        # datetimeはtimestampで保存されているためtimestampに変換
        cursor = await db.execute('SELECT * FROM bump where user_id = ? and bump_datetime = ?',
                                  (user_id, bump_datetime.timestamp()))
        data = await cursor.fetchone()
        if not data:
            return False
        return True


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
        await create_new_bump_data(212513828641046529, year_before, random.random(), 1)
        year_before += datetime.timedelta(hours=2)

