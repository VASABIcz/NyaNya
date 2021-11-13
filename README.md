![Discord.py-Version](https://img.shields.io/badge/discord.py-1.7.3-blue?style=flat-square)
![Code-Lines](https://img.shields.io/tokei/lines/github/VASABIcz/NyaNya?style=flat-square)
[![Discord Bots](https://top.gg/api/widget/owner/841271270015893535.svg)](https://top.gg/bot/841271270015893535)

# Nya Nya bot

### cfg.py structure

```python
class Base:
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
                      },
             'FREE': { # Found some free hosted nodes i think in germany so enjoy
                 'host': 'lava.link',
                 'port': 80,
                 'rest_uri': 'http://lava.link:80',
                 'password': 'anything',
                 'identifier': 'FREE',
                 'region': 'europe'
             },
             'ALSO_FREE': {
                 'host': 'lavalink.darrennathanael.com',
                 'port': 80,
                 'rest_uri': 'https://lavalink.darrennathanael.com',
                 'password': 'pw',
                 'identifier': 'FREE2',
                 'region': 'europe'
             }}
    
    # API'S
    CONVERT_API = ""     # place your api keys
    SPOTIFY_ID = ""      # all of them are free
    SPOTIFY_SECTRET = "" # 
    LOL_API_KEY = ""     # 

class Instance(Base):
    def __init__(self, **kwargs):
        self.OWNERS = kwargs.pop("OWNERS", self.OWNERS)
        self.TOKEN = kwargs.pop("TOKEN", self.TOKEN)
        self.MAIN_PREFIX = kwargs.pop("MAIN_PREFIX", self.MAIN_PREFIX)
        self.VOTE = kwargs.pop("VOTE", self.VOTE)
        self.SUPPORT = kwargs.pop("SUPPORT", self.SUPPORT)
        self.DEFAULT_EMOJI = kwargs.pop("DEFAULT_EMOJI", self.DEFAULT_EMOJI)
        self.ERROR_WEBHOOK_URL = kwargs.pop("ERROR_WEBHOOK_URL", self.ERROR_WEBHOOK_URL)
        self.REPORT_WEBHOOK_URL = kwargs.pop("REPORT_WEBHOOK_URL", self.REPORT_WEBHOOK_URL)
        self.DB_CREDENTIALS = kwargs.pop("DB_CREDENTIALS", self.DB_CREDENTIALS)
        self.RESOURCES_URL = kwargs.pop("RESOURCES_URL", self.RESOURCES_URL)
        self.NODES = kwargs.pop("NODES", self.NODES)
        self.CONVERT_API = kwargs.pop("CONVERT_API", self.CONVERT_API)
        self.SPOTIFY_ID = kwargs.pop("SPOTIFY_ID", self.SPOTIFY_ID)
        self.SPOTIFY_SECTRET = kwargs.pop("SPOTIFY_SECTRET", self.SPOTIFY_SECTRET)
        self.LOL_API_KEY = kwargs.pop("LOL_API_KEY", self.LOL_API_KEY)

# used to create multiple instances of your bot
INSTANCES = [
    Instance(), # 1st instance using default cfg
    #Instance(TOKEN="xxxx", MAIN_PREFIX="oj") 2nd instance using specified token and prefix
]
```

---

### In order to use voice you need to have `java` and setuped `Lavalink`

#### Check out [Setup instructions](https://github.com/VASABIcz/bot_framework/tree/master/utils/lavalink_server)
