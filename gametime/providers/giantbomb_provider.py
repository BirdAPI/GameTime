from providers import *

from gametime.mygame import MyGame
from GiantBomb import giantbomb

API_KEY = 'd6a03ad2843f7306e828b5b4f5e435af08f06a22'
    
class GiantBombProvider(GameProvider):
    def __init__(self):
        GameProvider.__init__(self)
        self.site_id = "giantbomb"
        self.site_name = "GiantBomb"
        self.table_name = "GiantBombInfo"
        self.search_tmpl = "searchGiantBomb.tmpl"
        self.info_tmpl = "giantbombInfo.tmpl"
        self.favicon = "giantbomb.png"
        self.favicon_blank = "giantbomb_blank.png"
        self.xref_id_column = "giantbomb_id"
        self.is_multi_system = True
        
        self.api = giantbomb.Api(API_KEY)
        
    def search(self, query, *args, **kwargs):
        srs = self.api.search(query)
        return [ self.get_info(None, sr.id) for sr in srs ]

    def new_info(self):
        return GiantBombInfo()

    def get_info(self, game_id, info_id):
        return GiantBombInfo(self.api.getGame(int(info_id)), MyGame.get(game_id).system if game_id else None)

class GiantBombInfo:
    def __init__(self, gb=None, system=None):
        self.id = None
        self.title = None
        self.summary = None
        self.boxart = None
        self.link = None
        self.release_date = None
        self.system = None
        self.systems = None
        if gb:
            self.initialize(gb, system)

    def initialize(self, gb, system):
        self.id = gb.id
        self.title = gb.name
        self.summary = gb.deck
        self.boxart = gb.image.thumb if gb.image else None
        self.link = gb.site_detail_url
        self.release_date = gb.original_release_date
        self.system = system
        self.systems = [normalize_system(p.name) for p in gb.platforms]
        
    @staticmethod
    def from_game(gb, system=None):
        return GiantBombInfo(gb, system)
        
provider = GiantBombProvider()
