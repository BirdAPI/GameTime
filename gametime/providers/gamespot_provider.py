from providers import *

from gamespot import gamespot
from gamespot.gamespot import Gamespot, GamespotInfo

class GamespotProvider(GameProvider):
    def __init__(self):
        GameProvider.__init__(self)
        self.site_id = "gamespot"
        self.site_name = "Gamespot"
        self.table_name = "GamespotInfo"
        self.search_tmpl = "searchGamespot.tmpl"
        self.info_tmpl = "gamespotInfo.tmpl"
        self.favicon = "gamespot.png"
        self.favicon_blank = "gamespot_blank.png"
        self.xref_id_column = "gamespot_id"
        
    def search(self, query, *args, **kwargs):
        return Gamespot.search(query)

    def new_info(self):
        return GamespotInfo()

    def get_info(self, game_id, info_id):
        return Gamespot.get_info(info_id)           
        
    
provider = GamespotProvider()
