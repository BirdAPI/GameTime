from providers import *

from IGN import ign
from IGN.ign import IGN, IGNInfo

class IGNProvider(GameProvider):
    def __init__(self):
        GameProvider.__init__(self)
        self.site_id = "ign"
        self.site_name = "IGN"
        self.table_name = "IGNInfo"
        self.search_tmpl = "searchIGN.tmpl"
        self.info_tmpl = "ignInfo.tmpl"
        self.favicon = "ign.png"
        self.xref_id_column = "ign_id"
        
    def search(self, query, *args, **kwargs):
        return IGN.search(query)

    def new_info(self):
        return IGNInfo()

    def get_info(self, game_id, info_id):
        return IGN.get_info(info_id)           
        
    
provider = IGNProvider()
