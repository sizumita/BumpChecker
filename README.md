# BumpChecker
disboard[https://disboard.org/ja] のbumpの結果を収集し、ランキング表示ができるBotです。

# ファイルについて
gitに上がっている以外に`bumpchecker.db`と`.env`ファイルがあります。
`bumpchecker.db`は自動生成されます。名前を変えたい場合は`database.py`にある設定を変更してください。

以下に、`.env`の中身を書きます。同じ内容を書いてください。

```text
TOKEN=あなたのBotトークン
NOTICE_CHANNEL_ID=bumpをするお知らせをしたいチャンネルのid（複数ある場合は,で仕切ってください。）
NOTICE_MESSAGE=bumpのお知らせのメッセージ
CAN_COMMAND_ROLES=あなたがBotのコマンドを実行するのを許可する役職idを書いてください。（複数ある場合は,で仕切ってください。）
                  書かなければ全ての人が使えます。
PREFIX=! (あなたがBotのプレフィックスに使用したい文字を入れてください。設定されていない場合、自動的に!になります。)
```

# 必要なライブラリ
```text
discord.py>=1.0.0
aiosqlite>=0.10.0
python-dotenv
```
