import gametime
from gametime.mygame import MyGame

from providers import *

from gametrailers import gametrailers
from gametrailers.gametrailers import GT, GTInfo

class GTProvider(GameProvider):
    def __init__(self):
        GameProvider.__init__(self)
        self.site_id = "gt"
        self.site_name = "Gametrailers"
        self.table_name = "GTInfo"
        self.search_tmpl = "searchGT.tmpl"
        self.info_tmpl = "gtInfo.tmpl"
        self.favicon = "gametrailers.png"
        self.xref_id_column = "gametrailers_id"
        self.ignore_list = ["systems"]
        
    def search(self, query, *args, **kwargs):
        return GT.search(query)

    def new_info(self):
        return GTInfo()

    def get_info(self, game_id, info_id):
        return GT.get_info(info_id, MyGame.get(game_id).system)           
    
    """
    Have to override this because gametrailers lumps all games of diff systems into one game id
    """    
    def get_match(self, title, system):
        title_norm = normalize_game_title(title)
        system_norm = normalize_system(system)
        results = self.search(title)
        for result in results:
            systems = [ normalize_system(system) for system in result.systems ]
            if system_norm in systems:
                if normalize_game_title(self.get_title(result)) == title_norm:
                    return self.get_id(result)
        return None
        
provider = GTProvider()
