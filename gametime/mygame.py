from datetime import datetime
from mydate import MyDate
import db
import gametime

class MyGame:
    def __init__(self):
        self.id = None
        self.title = None
        self.system = None
        self.boxart = None
        self.release_date = None
        self.summary = None
        
        self.metacritic_id = None
        self.ign_id = None
        self.giantbomb_id = None
        self.gamespot_id = None
        self.thegamesdb_id = None
        self.vgreleases_id = None
        self.vgchartz_id = None
        self.gamestop_id = None
        self.gametrailers_id = None
        self.amazon_asin = None
        
        self.date_added = None
        self.downloaded = None
        self.my_rating = None
        
        self.developer = None
        self.publisher = None
        self.developer_link = None
        self.publisher_link = None
        self.official_site = None
        self.esrb = None
        self.esrb_reason = None
            
    @property
    def my_date(self):
        return MyDate(self.release_date)
    
    def set_provider_id(self, provider, value):
        self.__dict__[provider.xref_id_column] = value
    
    def get_provider_id(self, provider):
        return self.__dict__[provider.xref_id_column] if provider.xref_id_column in self.__dict__ else None
    
    """
    Updates MyGame with GameInfo values. Will only fill
    in the empty values, unless force=True
    """
    def update_info(self, provider, info, force=False):
        if not info or not provider:
            return
        if not self.boxart or (force and provider.get_boxart(info)):
            self.boxart = provider.get_boxart(info)
        if not self.system or (force and provider.get_system(info)):
            self.system = game_matcher.normalize_system(provider.get_system(info))
        if not self.title or (force and provider.get_title(info)):
            self.title = provider.get_title(info)
        if not self.summary or (force and provider.get_summary(info)):
            self.summary = provider.get_summary(info)
        if not self.developer or (force and provider.get_developer(info)):
            self.developer = provider.get_developer(info)     
        if not self.publisher or (force and provider.get_publisher(info)):
            self.publisher = provider.get_publisher(info)
        if not self.developer_link or (force and provider.get_developer_link(info)):
            self.developer_link = provider.get_developer_link(info)            
        if not self.publisher_link or (force and provider.get_publisher_link(info)):
            self.publisher_link = provider.get_publisher_link(info)               
        if not self.official_site or (force and provider.get_official_site(info)):
            self.official_site = provider.get_official_site(info)
        if not self.esrb or (force and provider.get_esrb(info)):
            self.esrb = provider.get_esrb(info)
        if not self.esrb_reason or (force and provider.get_esrb_reason(info)):
            self.esrb_reason = provider.get_esrb_reason(info)
        old_date = self.my_date
        new_date = MyDate(provider.get_release_date(info))
        compl = MyDate.compare_completeness(new_date, old_date)
        # new date is more complete than old date, or new date and old date are same completeness, but new date is earlier than old date
        if not old_date or (compl < 0 or (compl == 0 and (force or MyDate.compare_dates(new_date, old_date)) < 0)):
            self.release_date = str(MyDate(provider.get_release_date(info)))
        self.update_in_db()
    
    def update_all_infos(self, **provider_infos):
        for provider, info in provider_infos.items():
            self.update_info(provider, info)

    def insert_in_db(self):
        self.id = None
        last_id = db.insert_generic(self, gametime.DATABASE_FILENAME, "MyGame")
        self.id = last_id
        
    def update_in_db(self):
        db.update_generic(self, gametime.DATABASE_FILENAME, "MyGame")
     
    @staticmethod    
    def delete_from_db(id):
        db.delete(id, "id", gametime.DATABASE_FILENAME, "MyGame")

    """
    Retreives the MyGame from the database that matches this id
    """
    @staticmethod
    def get(id):
        row = db.db_fetch_one(gametime.DATABASE_FILENAME, "SELECT * FROM MyGame WHERE id = ?", [id])
        return db.get_generic(MyGame(), row, False) if row else None

    """
    Retreives all MyGame items in the database
    """
    @staticmethod
    def get_all():
        rows = db.db_fetch_all(gametime.DATABASE_FILENAME, "SELECT * FROM MyGame")
        return [ db.get_generic(MyGame(), row, False) for row in rows ]
    
    @staticmethod
    def get_all_ids():
        rows = db.db_fetch_all(gametime.DATABASE_FILENAME, "SELECT id FROM MyGame")
        return [ row["id"] for row in rows ]
    
