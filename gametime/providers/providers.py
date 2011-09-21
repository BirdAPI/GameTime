import gametime
import gametime.db as db
import re

class GameProvider:
    def __init__(self):
        self.site_id = None
        self.site_name = None
        self.table_name = None
        self.search_tmpl = None
        self.info_tmpl = None
        self.favicon = None
        self.favicon_blank = None
        # The column in MyGame that points to this provider: MyGame.thisprovider_id
        self.xref_id_column = None
        self.id_column = "id"
        self.ignore_list = []
        # MultiSystem is a provider that uses the same id for the same game on different systems
        self.is_multi_system = False
        
    """
    Returns a list of search results
    """
    def search(self, query, *args, **kwargs):
        return None
        
    """
    Returns a new GameInfo object (the provider specific one)
    """
    def new_info(self):
        return None
    
    """
    Given an id, retreive the GameInfo object from the internet
    """
    def get_info(self, game_id, info_id):
        return None
    
    """
    Perform a search and match the search result, then return the game info id
    """
    def get_match(self, title, system):
        title_norm = normalize_game_title(title)
        system_norm = normalize_system(system)
        results = self.search(title)
        for result in results:
            systems = [ normalize_system(system) for system in self.get_systems(result) ]
            if system_norm in systems:
                if normalize_game_title(self.get_title(result)) == title_norm:
                    return self.get_id(result)
        return None
        
    """
    Retreives the item from the database that matches this id
    """
    def get_one(self, info_id):
        row = db.db_fetch_one(gametime.DATABASE_FILENAME, "SELECT * FROM [{0}] WHERE [{1}] = ?".format(self.table_name, self.id_column), [info_id])
        return db.get_generic(self.new_info(), row, False) if row else None

    """
    Retreives all items in the database for this provider
    """
    def get_all(self):
        rows = db.db_fetch_all(gametime.DATABASE_FILENAME, "SELECT * FROM [{0}]".format(self.table_name))
        return [ db.get_generic(self.new_info(), row, False) for row in rows ]
        
    """
    Gets the GameInfo for this particular game and updates it in the db
    """
    def update_in_db(self, info):
        db.update_generic(info, gametime.DATABASE_FILENAME, self.table_name, self)
        
    def insert_in_db(self, info):
        db.insert_generic(info, gametime.DATABASE_FILENAME, self.table_name, self)
    
    def insert_or_update_in_db(self, info):
        db.insert_or_update_generic(info, gametime.DATABASE_FILENAME, self.table_name, self)
    
    """
    These should only need to be overriden if the provider isnt standardized
    """
    def get_id(self, info):
        return try_get(info, "id")
    
    def get_link(self, info):
        return try_get(info, "link", "info_link", "url", "info_url")
    
    def get_boxart(self, info):
        return try_get(info, "boxart")
    
    def get_title(self, info):
        return try_get(info, "title", "name")
    
    def get_system(self, info):
        return try_get(info, "system", "platform") 
        
    def get_summary(self, info):
        return try_get(info, "summary", "description", "deck") 
    
    def get_release_date(self, info):
        return try_get(info, "release_date", "release_date_text", "original_release_date")
    
    def get_esrb(self, info):
        return try_get(info, "esrb", "esrb_rating")
    
    def get_esrb_reason(self, info):
        return try_get(info, "esrb_reason")
    
    def get_developer(self, info):
        return try_get(info, "developer", "dev")
    
    def get_publisher(self, info):
        return try_get(info, "publisher", "pub")
    
    def get_developer_link(self, info):
        return try_get(info, "developer_link", "dev_link")
    
    def get_publisher_link(self, info):
        return try_get(info, "publisher_link", "pub_link")
    
    def get_official_site(self, info):
        return try_get(info, "official_site", "official_url", "official_link")
    
    def get_systems(self, info):
        systems = try_get(info, "systems", "platforms")
        return systems if systems else [ self.get_system(info) ]



    
def try_get(obj, *attr_names):
    for attr in attr_names:
        try:
            return obj.__dict__[attr]
        except KeyError:
            pass
    return None

def normalize_system(system):
    if not system:
        return None
    s = system.lower().replace("-", "").replace("_", "").replace(" ", "")
    if s in ["x360", "xbox360", "xb360"]:
        return "Xbox 360"
    elif s in ["ps3", "playstation3"]:
        return "PS3"
    elif s in ["wii", "nintendowii"]:
        return "Wii"
    elif s in ["psp", "playstationportable"]:
        return "PSP"
    elif s in ["ds", "nintendods"]:
        return "DS"
    elif s in ["3ds", "nintendo3ds"]:
        return "3DS"
    elif s in ["ps", "ps1", "playstation1"]:
        return "PS1"
    elif s in ["ps2", "playstation2"]:
        return "PS2"
    elif s in ["pc", "computer", "personalcomputer"]:
        return "PC"
    elif s in ["psvita", "vita", "playstationvita"]:
        return "PS Vita"
    elif s in ["nes", "nintendo", "nintendoentertainmentsystem"]:
        return "NES"
    elif s in ["snes", "supernintendo", "supernes"]:
        return "SNES"
    elif s in ["wiiware", "wiishop"]:
        return "Wii Ware"
    elif s in ["playstationnetwork", "psn"] or s.startswith("playstationnetwork"):
        return "PSN"
    elif s in ["xbl", "xboxlive", "xblarcade", "xboxlivearcade"]:
        return "XBL Arcade"
    else:
        return system
        
TITLE_REPLACES = { 
                    ":" : "",
                    "," : "",
                    "\." : "",
                    "_" : "",
                    "-" : "",
                    "\+" : "",
                    " XIII( |$)" : "13",
                    " VIII( |$)" : "8",
                    " VII( |$)" : "7",
                    " XII( |$)" : "12",
                    " XIV( |$)" : "14",
                    " XV( |$)" : "15",
                    " III( |$)" : "3",
                    " IV( |$)" : "4",
                    " V( |$)" : "5",
                    " VI( |$)" : "6",
                    " II( |$)" : "2",
                    " IX( |$)" : "9",
                    " XI( |$)" : "11",
                    " X( |$)" : "10",
                    "(^T| t)he " : "",
                    " of " : "",
                    " and " : "",
                    " a " : "",
                    "A " : "",
                    "'" : ""
                   }

def normalize_game_title(title, echo=True):
    if not title:
        return None
    res = title
    for (key, value) in TITLE_REPLACES.items():
        res = re.sub(key, value, res)
    res = res.replace(" ", "").lower()
    if echo:
        print title, "->", res
    return res
