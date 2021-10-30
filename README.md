![Discord.py-Version](https://img.shields.io/badge/discord.py-1.7.3-blue?style=flat-square)
![Code-Lines](https://img.shields.io/tokei/lines/github/VASABIcz/NyaNya?style=flat-square)
[![Discord Bots](https://top.gg/api/widget/owner/841271270015893535.svg)](https://top.gg/bot/841271270015893535)

# Nya Nya bot

### cfg.py structure

```python
# OWNERS
OWNERS = [] # your discord id

# SETUP
TOKEN = "" # bot token
MAIN_PREFIX = "nya." # your prefix
VOTE = 'https://top.gg/' # top gg url | could be entirely different
SUPPORT = 'https://discord.com/' # if you have support server | also purely optional
DEFAULT_EMOJI = '❓' # default emoji displayed in help for cogs
ERROR_WEBHOOK_URL = "" # your webhook for errors        # BOTH
REPORT_WEBHOOK_URL = "" # your webhook for exceptions   # OPTIONAL

# BACKEND
DB_CREDENTIALS = {"user": "postgres", "password": "postgres", "database": "postgres", "host": "db"} # postgres cred in compose | should be changed !
RESOURCES_URL = "https://raw.githubusercontent.com/VASABIcz/NyaNya/master/resources/" # resources url (now just for help image)
NODES = {'MAIN': {'host': 'lavalink',     # default lavalink creds | could stay the same
                  'port': 2333,
                  'rest_uri': 'http://lavalink:2333',
                  'password': 'youshallnotpass',
                  'identifier': 'MAIN',
                  'region': 'europe'
                  }}

# API'S
CONVERT_API = ""     # place your api keys
SPOTIFY_ID = ""      # all of them are free
SPOTIFY_SECTRET = "" # 
LOL_API_KEY = ""     # 
```

---

### In order to use voice you need to have `java` and setuped `Lavalink`

#### Check out [Setup instructions](https://github.com/VASABIcz/bot_framework/tree/master/utils/lavalink_server)
