import asyncio
import datetime
import os
import re
import sys
import traceback
from os.path import join, dirname
from statistics import mean

import discord
from discord.ext import commands
from dotenv import load_dotenv

from database import *

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)
disboard_bot_id = 302050872383242240  # disboardのBotのユーザーid
bump_notice_channel_id, can_command_roles, bump_notice_message, prefix = None, None, None, None


def load():
    global bump_notice_channel_id, can_command_roles, bump_notice_message, prefix
    try:
        bump_notice_channel_id = [
            *map(int, os.environ.get("NOTICE_CHANNEL_ID").split(","))]  # bumpの通知をするチャンネルのidのリストです。無ければ空のままにしておいてください。
    except Exception:
        bump_notice_channel_id = []
    try:
        bump_notice_message = os.environ.get("NOTICE_MESSAGE")  # bumpの通知のメッセージです。
    except Exception:
        bump_notice_message = "もうすぐbumpする時間ですよ！"
    try:
        # コマンドを実行できる権限の一覧です。
        can_command_roles = [*map(int, os.environ.get("CAN_COMMAND_ROLES").split(","))].append(212513828641046529)
    except AttributeError:
        can_command_roles = []
    try:
        text = os.environ.get('PREFIX')
        if text is None:
            prefix = '!'
        if ' ' in text:
            prefix = text.split()
        else:
            prefix = text
    except AttributeError:
        prefix = '!'


bump_notice_timing = 5  # お知らせをするタイミング 初期設定はbumpする時間の５分前
load()


class MyBot(commands.Bot):
    def __init__(self, command_prefix, **options):
        super().__init__(command_prefix, **options)
        self.last_bumped_datetime = None
        self.miss_users = []

    async def on_ready(self):
        await create_table()
        print('Bot is on ready.(ﾟ∀ﾟ)')

    async def break_five_minutes(self):
        """bumpしてから5分後までの!disboard bumpはバンプ制限を解除"""
        await asyncio.sleep(5 * 60)
        self.miss_users = []

    async def bump_notice(self):
        """bumpのお知らせをする"""

        # チャンネルidがなかった場合処理しない
        if not bump_notice_channel_id:
            return

        notice_datetime = self.last_bumped_datetime + datetime.timedelta(hours=2) - datetime.timedelta(
            minutes=bump_notice_timing)
        now = datetime.datetime.utcnow()
        await asyncio.sleep(notice_datetime.timestamp() - now.timestamp())

        # 送信する
        for _id in bump_notice_channel_id:
            channel = self.get_channel(_id)
            await channel.send(bump_notice_message)

    async def on_message(self, message: discord.Message):
        if message.author.id == disboard_bot_id:
            if "このサーバーを上げられるようになるまであと" in message.embeds[0].description:
                await self.miss_disboard_command(message)
                return
            await self.check_disboard_message(message)
        await self.process_commands(message)

    async def miss_disboard_command(self, message: discord.Message):
        """bumpをミスした場合"""
        user = message.guild.get_member(int(re.search('<(!@|@)([0-9]+)>', message.embeds[0].description).groups()[1]))
        print(f'User {user.name} is missed `!disboard bump`')
        self.miss_users.append(user.id)
        if not self.last_bumped_datetime:
            near = 0
        else:
            near = message.created_at.timestamp() - (
                    self.last_bumped_datetime + datetime.timedelta(hours=2)).timestamp()
        await create_new_bump_data(user.id, message.created_at, float(near), 0)

    async def check_disboard_message(self, message: discord.Message):
        """disboardのメッセージを解析して、誰がbumpに成功したのか判定"""
        content = message.embeds[0].description
        if not '表示順をアップしたよ' in content:
            return
        user = message.guild.get_member(int(re.search('<(!@|@)([0-9]+)>', message.embeds[0].description).groups()[1]))
        print(f'User {user.name} is successful `!disboard bump`')
        if user.id in self.miss_users:
            await self.bump_request_failed(user, message)
        else:
            await self.bump_request_succeeded(user, message)
        self.loop.create_task(self.bump_notice())
        self.miss_users = []
        self.loop.create_task(self.break_five_minutes())

    async def bump_request_failed(self, user, message: discord.Message):
        """すでに打っていた場合"""
        embed = discord.Embed(title="あなたはすでにbumpに失敗しています！", description="１回のbumpチャレンジで打てるコマンドの回数は１回のみです。")
        await message.channel.send(embed=embed)
        if not self.last_bumped_datetime:
            near = 0
        else:
            near = message.created_at.timestamp() - (
                    self.last_bumped_datetime + datetime.timedelta(hours=2)).timestamp()
        await create_new_bump_data(user.id, message.created_at, float(near), 0)
        self.last_bumped_datetime = message.created_at
        embed = discord.Embed(title="セット完了", description="次回のbumpの計測を開始しました。")
        await message.channel.send(embed=embed)

    async def bump_request_succeeded(self, user, message: discord.Message):
        """成功した場合"""
        if not self.last_bumped_datetime:
            near = 0
        else:
            near = message.created_at.timestamp() - (
                    self.last_bumped_datetime + datetime.timedelta(hours=2)).timestamp()
        await create_new_bump_data(user.id, message.created_at, float(near), 1)

        await message.channel.send(embed=discord.Embed(title="Bump成功！", description=f"{str(user)}が成功しました。誤差: {near}秒"))

        self.last_bumped_datetime = message.created_at
        embed = discord.Embed(title="セット完了", description="次回のbumpの計測を開始しました。")
        await message.channel.send(embed=embed)

    async def on_command_error(self, context, exception):
        if isinstance(exception, commands.CommandNotFound):
            return
        exception = exception.original
        traceback.print_exception(type(exception), exception, exception.__traceback__, file=sys.stderr)


bot = MyBot(prefix)


def check_user_roles(ctx):
    if not can_command_roles:
        return True
    for role in ctx.author.roles:
        if role.id in can_command_roles:
            return True
    return False


@bot.command(name='ranking')
async def get_ranking(ctx, datetime1='all', datetime2='', count=100):
    if not check_user_roles(ctx):
        return

    print(f'User {ctx.author.name} use ranking command.')
    if datetime1 == 'all':
        user_data = await get_all_bump_data()
        _range = ''
    else:
        #  2019/05/26-00:00:00 <- 書式 適宜に変更してください
        try:
            tdatetime1 = datetime.datetime.strptime(datetime1, '%Y/%m/%d-%H:%M:%S')
            tdatetime2 = datetime.datetime.strptime(datetime2, '%Y/%m/%d-%H:%M:%S')
            user_data = await get_range_bump_data_(tdatetime1, tdatetime2)
            _range = f'{tdatetime1}~{tdatetime2}'
        except Exception:
            await ctx.send('datetimeの書式が間違っています。')
            return
    _user_data = []
    for user in user_data:
        user['count'] = -user['count']
        user['near'] = mean(user['nears'])
        _user_data.append(user)

    sorted_user_data = sorted(
        _user_data,
        key=lambda x: (x['count'], x['near'])
    )
    top = 1
    while True:
        embed = discord.Embed(title="Bumperランキング", description=f'top{top}~top{top + 19}')
        for x in range(20):
            if not sorted_user_data or top == count:
                top = -1
                break
            user = sorted_user_data.pop(0)
            try:
                member = await ctx.guild.fetch_member(user['id'])
            except discord.NotFound:
                member = "存在しないユーザー"
            embed.add_field(name=f'No.{top} {str(member)} id:{user["id"]}',
                            value=f'カウント:{-user["count"]}回  平均誤差:{round(user["near"], 3)}秒',
                            inline=False)
            top += 1
            count -= 1
        await ctx.send(embed=embed)
        if top == -1 or not sorted_user_data:
            break


# @bot.command(name='putrole')
# async def put_role(ctx, before, after, role: discord.Role, r: int):
#     await ctx.send('付与を開始します。')
#     try:
#         before = datetime.datetime.strptime(before, '%Y/%m/%d-%H:%M:%S')
#         after = datetime.datetime.strptime(after, '%Y/%m/%d-%H:%M:%S')
#         _range = f'{before}~{after}'
#     except Exception:
#         await ctx.send('datetimeの書式が間違っています。')
#         return
#     user_ids = await get_range_bump_data_(before, after)
#     user_ids = list(user_ids.keys())
#     c = collections.Counter(user_ids)
#     counts = collections.defaultdict(list)
#     for _id, count in c.most_common():
#         counts[count].append(_id)
#
#     ranking = []
#     for count, users in sorted(counts.items(), reverse=True):
#         if len(users) == 1:
#             ranking.append(users[0])
#             continue
#
#         o = {await get_user_near_average(i, before, after): i for i in users}
#         for av, _id in sorted(o.items()):
#             ranking.append(_id)
#
#     for _id in ranking[:r]:
#         member = ctx.guild.get_member(_id)
#         await member.add_roles(role)
#     await ctx.send('付与終了しました。')


@bot.command(name='load')
async def load_old_data(ctx, message_id):
    """メッセージidを指定することで、過去のdisboardの投稿を記録可能"""
    if not check_user_roles(ctx):
        return

    if ',' in message_id:
        message_id_list = [int(i) for i in message_id.split(',')]
    else:
        message_id_list = [int(message_id)]
    for _id in message_id_list:
        message = await ctx.channel.fetch_message(_id)
        user = message.guild.get_member(int(re.search('<(!@|@)([0-9]+)>', message.embeds[0].description).groups()[1]))
        # ここでメッセージをdisboardのものと判定
        if not message.author.id == disboard_bot_id:
            await ctx.send('それはdisboardのメッセージではありません。')
            continue
        # 次にメッセージがすでにないか確認
        if await check_data(user.id, message.created_at):
            await ctx.send('すでに存在します')
        else:
            # 入れる
            if "このサーバーを上げられるようになるまであと" in message.embeds[0].description:
                near = int(message.embeds[0].description.replace("このサーバーを上げられるようになるまであと", '', ).replace('分です', '')) * 60
                await create_new_bump_data(user.id, message.created_at, float(near), 0)

            elif "表示順をアップしたよ" in message.embeds[0].description:
                await create_new_bump_data(user.id, message.created_at, 0, 1)
            else:
                continue

            await ctx.send('追加処理完了しました。')
    await ctx.send('全ての処理が終了しました。')


async def get_user_near_average(user_id, before, after):
    d, nears = await get_range_user_data(user_id, before, after)
    return sum(nears) / len(nears)


@bot.command(name='reload')
async def reload_dotenv(ctx):
    """dotenvファイルを再読み込みします。administrator専用です。"""
    if ctx.author.guild_permissions.administrator:
        await ctx.send('reloadします...')
        load_dotenv(dotenv_path)
        load()
        await ctx.send('reload完了しました。')
    else:
        await ctx.send('administrator権限がありません。実行できません。')


@bot.command(name='roles')
async def roles(ctx):
    """roleの名前とidを取得します。administrator専用です。"""
    if ctx.author.guild_permissions.administrator:
        text = '```\n'
        for role in ctx.guild.roles:
            text += f'{role.name}: {role.id}\n'
        text += '```'
        await ctx.send(text[:2000])


if __name__ == '__main__':
    bot.run(os.environ.get("TOKEN"))
