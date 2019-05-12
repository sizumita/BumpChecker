import asyncio
import datetime
import os
from os.path import join, dirname

import discord
from discord.ext import commands
from dotenv import load_dotenv

from database import *

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

disboard_bot_id = 302050872383242240  # disboardのBotのユーザーid
try:
    bump_notice_channel_id = [int(i) for i in os.environ.get("NOTICE_CHANNEL_ID").split(
        ',')]  # bumpの通知をするチャンネルのidのリストです。無ければ空のままにしておいてください。
except Exception:
    bump_notice_channel_id = []
try:
    bump_notice_message = os.environ.get("NOTICE_MESSAGE")  # bumpの通知のメッセージです。
except Exception:
    bump_notice_message = "もうすぐbumpする時間ですよ！"
bump_notice_timing = 5  # お知らせをするタイミング 初期設定はbumpする時間の５分前


class MyBot(commands.Bot):
    def __init__(self, command_prefix, **options):
        super().__init__(command_prefix, **options)
        self.last_bumped_datetime = None
        self.last_bump_user_id = None

    async def on_ready(self):
        await create_table()

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
            # embedの場合
            if isinstance(bump_notice_message, discord.Embed):
                await channel.send(embed=bump_notice_message)

            else:
                await channel.send(bump_notice_message)

    async def on_message(self, message: discord.Message):
        if message.author.id == disboard_bot_id:
            if "このサーバーを上げられるようになるまであと" in message.embeds[0].description:
                return
            await self.check_disboard_message(message)
        await self.process_commands(message)

    async def check_disboard_message(self, message: discord.Message):
        """disboardのメッセージを解析して、誰がbumpに成功したのか判定"""
        content = message.embeds[0].description
        if not '表示順をアップしたよ' in content:
            return
        user_id = message.content.replace('<@', '').replace('!', '').replace('>', '')
        if self.last_bump_user_id == int(user_id):
            await self.bump_request_failed(int(user_id), message)
        else:
            await self.bump_request_succeeded(int(user_id), message)
        self.loop.create_task(self.bump_notice())

    async def bump_request_failed(self, user_id, message: discord.Message):
        """二回連続で失敗した場合"""
        embed = discord.Embed(title="連続でbumpをすることはできません！", description="連続でbumpに成功しても反映されません。")
        await message.channel.send(embed=embed)
        self.last_bumped_datetime = message.created_at
        embed = discord.Embed(title="セット完了", description="次回のbumpの計測を開始しました。")
        await message.channel.send(embed=embed)

    async def bump_request_succeeded(self, user_id, message: discord.Message):
        """成功した場合"""
        if not self.last_bumped_datetime:
            near = 0
        else:
            near = message.created_at.timestamp() - (
                    self.last_bumped_datetime + datetime.timedelta(hours=2)).timestamp()
        user = self.get_user(user_id)
        await create_new_bump_data(user.id, message.created_at, float(near))

        await message.channel.send(embed=discord.Embed(title="Bump成功！", description=f"{str(user)}が成功しました。誤差: {near}秒"))

        self.last_bumped_datetime = message.created_at
        embed = discord.Embed(title="セット完了", description="次回のbumpの計測を開始しました。")
        await message.channel.send(embed=embed)
        self.last_bump_user_id = user.id

    async def on_command_error(self, context, exception):
        pass


bot = MyBot('!')


@bot.command(name='ranking')
async def get_ranking(ctx, datetime1='all', datetime2='', count=100):
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

    for user in list(user_data):
        user_data[user]['near'] = sum(user_data[user]['nears']) / len(user_data[user]['nears'])
    _sorted = sorted(user_data.items(), key=lambda x: x[1]['count'], reverse=True)
    top = 1
    while True:
        embed = discord.Embed(title="Bumperランキング", description=f'top{top}~top{top + 19}')
        for x in range(20):
            if not _sorted or not count:
                break
            user = _sorted.pop(0)
            member = await ctx.guild.fetch_member(user[0])
            embed.add_field(name=f'No.{top} {str(member)} id:{user[0]}',
                            value=f'カウント:{user[1]["count"]}回  平均誤差:{user[1]["near"]}秒')
            top += 1
            count -= 1
        await ctx.send(embed=embed)
        if not _sorted or not count:
            break


if __name__ == '__main__':
    bot.run(os.environ.get("TOKEN"))
