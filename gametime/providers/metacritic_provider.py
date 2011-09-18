from providers import *

from metacritic import metacritic
from metacritic.metacritic import Metacritic, MetacriticInfo

class MetacriticProvider(GameProvider):
    def __init__(self):
        GameProvider.__init__(self)
        self.site_id = "metacritic"
        self.site_name = "Metacritic"
        self.table_name = "MetacriticInfo"
        self.search_tmpl = "searchMetacritic.tmpl"
        self.info_tmpl = "metacriticInfo.tmpl"
        self.favicon = "metacritic.png"
        self.favicon_blank = "metacritic_blank.png"
        self.xref_id_column = "metacritic_id"
        
    def search(self, query, *args, **kwargs):
        return Metacritic.search(query)

    def new_info(self):
        return MetacriticInfo()

    def get_info(self, game_id, info_id):
        return Metacritic.get_info(info_id)
        
    
provider = MetacriticProvider()
