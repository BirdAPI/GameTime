import gametime
from gametime.mygame import MyGame

from providers import *

from gametrailers import gametrailers
from gametrailers.gametrailers import GT, GTInfo

class GTProvider(GameProvider):
    def __init__(self):
        GameProvider.__init__(self)
        self.site_id = "gametrailers"
        self.site_name = "GameTrailers"
        self.table_name = "GTInfo"
        self.search_tmpl = "searchGT.tmpl"
        self.info_tmpl = "gtInfo.tmpl"
        self.favicon = "gametrailers.png"
        self.favicon_blank = "gametrailers_blank.png"
        self.xref_id_column = "gametrailers_id"
        self.ignore_list = ["systems"]
        self.is_multi_system = True
        
    def search(self, query, *args, **kwargs):
        return GT.search(query)

    def new_info(self):
        return GTInfo()

    def get_info(self, game_id, info_id):
        return GT.get_info(info_id, MyGame.get(game_id).system)           
    
        
provider = GTProvider()
