![Discord.py-Version](https://img.shields.io/badge/discord.py-1.7.3-blue?style=flat-square)
![Code-Lines](https://img.shields.io/tokei/lines/github/VASABIcz/NyaNya?style=flat-square)
[![Discord Bots](https://top.gg/api/widget/owner/841271270015893535.svg)](https://top.gg/bot/841271270015893535)

# Nya Nya bot

### cfg.py structure

```python
OWNERS=[] # YOUR DISCORD ID

MAIN_PREFIX= "nya" # prefix here

TOKEN = "" # DISCORD TOKEN HERE
SPOTIFY_ID = "" # app id here
SPOTIFY_SECTRET = "" # spotify api key here
LOL_API_KEY = "" # riot api key
ERROR_WEBHOOK_URL = "" # webhook wher will be errors send (optional)
REPORT_WEBHOOK_URL = "" # webhook wher will be reports send (optional)
DB_CREDENTIALS = {"user": "", "password": "", "database": "", "host": ""} #postgeresql credentials
NODES = {'MAIN': {'host': 'x.x.x.x',
                  'port': 2333,
                  'rest_uri': 'http://x.x.x.x:2333',
                  'password': 'youshallnotpass',
                  'identifier': 'MAIN',
                  'region': 'europe'
                  }} # Lavalink credentials change x.x.x.x for your server ip
                     # If its this machine change it to localhost
                     # aditionaly you can change region and password or add more nodes
```

---

### In order to use voice you need to have `java` and setuped `Lavalink`

#### Check out [Setup instructions](https://github.com/VASABIcz/bot_framework/tree/master/utils/lavalink_server)
