#!/usr/bin/python

import cherrypy.lib

from pprint import pprint
import sqlite3
import sys
import re
import os
import threading

import gametime

from cheetah.Template import Template

import game_matcher
from abgx360 import abgx360
from IGN import ign
from IGN.ign import IGN
from IGN.ign import IGNInfo
from metacritic import metacritic
from metacritic.metacritic import Metacritic, MetacriticInfo
from gamespot import gamespot
from gamespot.gamespot import Gamespot, GamespotInfo
from gametrailers import gametrailers
from gametrailers.gametrailers import GT, GTInfo
from mydate import MyDate
from mygame import MyGame

class WebInterface:

    @cherrypy.expose
    def index(self):
        t = Template(open(os.path.join(gametime.TMPL_DIR, "index.tmpl")).read())
        sqlQuery = "SELECT * FROM MyGame"
        conn = sqlite3.connect(gametime.DATABASE_FILENAME)
        conn.row_factory = sqlite3.Row
        mygames = [ get_generic_from_db(MyGame(), row) for row in conn.execute(sqlQuery).fetchall() ]
        mygames = sorted(mygames, key=lambda g: (g.my_date, g.title))
        t.mygames = mygames
        return munge(t)
    
    @cherrypy.expose
    def search(self, query, site):
        if site == "metacritic":
            t = Template(open(os.path.join(gametime.TMPL_DIR, "searchMetacritic.tmpl")).read())
            t.results = Metacritic.search(query, "game")
        elif site == "ign":
            t = Template(open(os.path.join(gametime.TMPL_DIR, "searchIGN.tmpl")).read())
            t.results = IGN.search(query, 10)
        elif site == "gamespot":
            t = Template(open(os.path.join(gametime.TMPL_DIR, "searchGameSpot.tmpl")).read())
            t.results = Gamespot.search(query)
        elif site == "gametrailers":
            t = Template(open(os.path.join(gametime.TMPL_DIR, "searchGT.tmpl")).read())
            t.results = GT.search(query)             
        t.info_site = site
        return munge(t)
    
    @cherrypy.expose
    def gameInfo(self, id):
        game = get_game(id)
        t = Template(open(os.path.join(gametime.TMPL_DIR, "gameInfo.tmpl")).read())
        t.game = game
        conn = sqlite3.connect(gametime.DATABASE_FILENAME)
        conn.row_factory = sqlite3.Row
        t.metacritic = get_generic_from_db(MetacriticInfo(), conn.execute("SELECT * FROM MetacriticInfo WHERE id = ?", [game.metacritic_id]).fetchone())
        t.ign = get_generic_from_db(IGNInfo(), conn.execute("SELECT * FROM IGNInfo WHERE id = ?", [game.ign_id]).fetchone())
        t.gamespot = get_generic_from_db(GamespotInfo(), conn.execute("SELECT * FROM GamespotInfo WHERE id = ?", [game.gamespot_id]).fetchone())
        t.gt = get_generic_from_db(GTInfo(), conn.execute("SELECT * FROM GTInfo WHERE id = ?", [game.gametrailers_id]).fetchone())
        conn.close()
        return munge(t)
    
    @cherrypy.expose
    def addGame(self, title, system, info_id, info_site):
        game = MyGame()
        game.title = title
        game.system = game_matcher.normalize_system(system)
      
        if info_site == "metacritic":
            game.metacritic_id = info_id
        elif info_site == "ign":
            game.ign_id = info_id
        elif info_site == "gamespot":
            game.gamespot_id = info_id
        elif info_site == "gametrailers":
            game.gametrailers_id = info_id
      
        insert_generic_into_db(game, gametime.DATABASE_FILENAME, "MyGame")
        game = get_game_from_title(game.title)
        
        if info_site == "metacritic":
            self.updateMetacriticInfo(game.id, info_id)
        elif info_site == "ign":
            self.updateIGNInfo(game.id, info_id)
        elif info_site == "gamespot":
            self.updateGamespotInfo(game.id, info_id)
        elif info_site == "gametrailers":
            self.updateGTInfo(game.id, info_id)
        
        raise cherrypy.HTTPRedirect("/")
    
    @cherrypy.expose
    def removeGame(self, id):
        try:
            sql = "DELETE FROM MyGame WHERE id = ?"
            #sql2 = "DELETE FROM MetacriticInfo WHERE id = ?"
            conn = sqlite3.connect(gametime.DATABASE_FILENAME)
            conn.execute(sql, [id])
            #conn.execute(sql2, [metacritic_id])
            conn.commit()
        except:
            print "Error trying to remove game: %s" % metacritic_id
        finally:
            conn.close()        
            raise cherrypy.HTTPRedirect("/")
    
    @cherrypy.expose
    def updateAllGames(self, redirect=True):
        conn = sqlite3.connect(gametime.DATABASE_FILENAME)
        ids = [ row[0] for row in conn.execute("SELECT id FROM MyGame").fetchall() ]
        for id in ids:
            self.updateGame(id, False)
        if redirect:
            raise cherrypy.HTTPRedirect("/")
    
    @cherrypy.expose
    def updateGame(self, id, redirect=True):
        game = get_game(id)
        self.updateIGNInfo(id, game.ign_id, False)
        self.updateMetacriticInfo(id, game.metacritic_id, False)
        self.updateGamespotInfo(id, game.gamespot_id, False)
        self.updateGTInfo(id, game.gametrailers_id, False)
        if redirect:
            raise cherrypy.HTTPRedirect("/")
    
    @cherrypy.expose
    def updateIGNInfo(self, id, ign_id=None, redirect=True):
        game = get_game(id)
        if not game:
            if redirect:
                raise cherrypy.HTTPRedirect("/")
            else:
                return
        if not ign_id:
            ign_id = game_matcher.match_to_ign(game.title, game.system)
        if not ign_id:
            if redirect:
                raise cherrypy.HTTPRedirect("/")
            else:
                return
        ign = IGN.get_info(ign_id)
        if ign:
            pprint(vars(ign))
            insert_generic_into_db(ign, gametime.DATABASE_FILENAME, "IGNInfo", replace_into=True)
            game.ign_id = ign.id
            update_my_game_info(game, ign=ign)
        if redirect:
            raise cherrypy.HTTPRedirect("/")
       
    @cherrypy.expose
    def updateMetacriticInfo(self, id, metacritic_id=None, redirect=True):
        game = get_game(id)
        if not game:
            if redirect:
                raise cherrypy.HTTPRedirect("/")
            else:
                return
        if not metacritic_id:
            metacritic_id = game_matcher.match_to_metacritic(game.title, game.system)
        if not metacritic_id:
            if redirect:
                raise cherrypy.HTTPRedirect("/")
            else:
                return
        metacritic = Metacritic.get_info(metacritic_id)
        if metacritic:
            pprint(vars(metacritic))
            insert_generic_into_db(metacritic, gametime.DATABASE_FILENAME, "MetacriticInfo", replace_into=True)
            game.metacritic_id = metacritic.id
            update_my_game_info(game, metacritic=metacritic)
        if redirect:
            raise cherrypy.HTTPRedirect("/")
        
    @cherrypy.expose
    def updateGamespotInfo(self, id, gamespot_id=None, redirect=True):
        game = get_game(id)
        if not game:
            if redirect:
                raise cherrypy.HTTPRedirect("/")
            else:
                return
        if not gamespot_id:
            gamespot_id = game_matcher.match_to_gamespot(game.title, game.system)
        if not gamespot_id:
            if redirect:
                raise cherrypy.HTTPRedirect("/")
            else:
                return
        gamespot = Gamespot.get_info(gamespot_id)
        if gamespot:
            pprint(vars(gamespot))
            insert_generic_into_db(gamespot, gametime.DATABASE_FILENAME, "GamespotInfo", replace_into=True)
            game.gamespot_id = gamespot_id
            update_my_game_info(game, gamespot=gamespot)
        if redirect:
            raise cherrypy.HTTPRedirect("/")
            
    @cherrypy.expose
    def updateGTInfo(self, id, gametrailers_id=None, redirect=True):
        game = get_game(id)
        if not game:
            if redirect:
                raise cherrypy.HTTPRedirect("/")
            else:
                return
        if not gametrailers_id:
            gametrailers_id = game_matcher.match_to_gametrailers(game.title, game.system)
        if not gametrailers_id:
            if redirect:
                raise cherrypy.HTTPRedirect("/")
            else:
                return
        gt = GT.get_info(gametrailers_id, game.system)
        if gt:
            pprint(vars(gt))
            insert_generic_into_db(gt, gametime.DATABASE_FILENAME, "GTInfo", ignore_list=['systems'], replace_into=True)
            game.gametrailers_id = gametrailers_id
            update_my_game_info(game, gametrailers=gt)
        if redirect:
            raise cherrypy.HTTPRedirect("/")
    
    @cherrypy.expose
    def verifyStealth(self):
        t = Template(open(os.path.join(gametime.TMPL_DIR, "verifyStealth.tmpl")).read())
        return munge(t)
        
    @cherrypy.expose    
    def doVerifyStealth(self, iso):
        t = Template(open(os.path.join(gametime.TMPL_DIR, "doVerifyStealth.tmpl")).read())
        t.iso = iso
        t.xex = "123456789"
        return munge(t)
    
    @cherrypy.expose
    def abgx360Patch(self, iso):
        (xex, ss_filename, dmi_filename) = abgx360.get_xex_game_patches(iso)
        if ss_filename is not None and dmi_filename is not None:
            print "Patching: %s to SSv2..." % iso
            patch_html_log = abgx360.stealth_patch_ssv2(iso, ss_filename, dmi_filename, xex)
            print "Done patching to SSv2."
            patch_success = abgx360.was_patch_successful(patch_html_log)
            if patch_success:
                print "Patching was successful!"
                return munge(open(patch_html_log).read())
            else:
                print "ERROR: Patching Failed!"  
                
    @cherrypy.expose
    def abgx360Verify(self, xex, iso):
        print "Verifying: %s..." % iso
        verify_html_log = abgx360.verify_stealth(iso, xex)
        print "Done verifying iso."
        stealth_success = abgx360.is_stealth_verified(verify_html_log, True)
        if stealth_success:
            print "Stealth check passed!"
            return munge(open(verify_html_log).read())
        else:
            print "ERROR: Stealh check failed!"

def get_game(id):
    conn = sqlite3.connect(gametime.DATABASE_FILENAME)
    conn.row_factory = sqlite3.Row
    game = get_generic_from_db(MyGame(), conn.execute("SELECT * FROM MyGame WHERE id = ?", [id]).fetchone())
    conn.close()
    return game
    
def get_game_from_title(title):
    conn = sqlite3.connect(gametime.DATABASE_FILENAME)
    conn.row_factory = sqlite3.Row
    game = get_generic_from_db(MyGame(), conn.execute("SELECT * FROM MyGame WHERE title = ?", [title]).fetchone())
    conn.close()
    return game
    
def update_my_game_info(game, metacritic=None, ign=None, gamespot=None, gametrailers=None): 
    infos = [metacritic, ign, gamespot, gametrailers]
    for info in infos:
        if not info:
            continue
        if not game.boxart:
            game.boxart = info.boxart
        if not game.system:
            game.system = game_matcher.normalize_system(info.system)
        if not game.title:
            game.title = info.title
        if not game.summary:
            game.summary = info.summary
        old_date = game.my_date
        new_date = MyDate(info.release_date)
        compl = MyDate.compare_completeness(new_date, old_date)
        # new date is more complete than old date, or new date and old date are same completeness, but new date is earlier than old date
        if not old_date or (compl < 0 or (compl == 0 and MyDate.compare_dates(new_date, old_date) < 0)):
            game.release_date = str(MyDate(info.release_date))
    update_generic_in_db(game, gametime.DATABASE_FILENAME, "MyGame")

def get_generic_from_db(object, row, include_extras=False):
    if row:
        for index, value in enumerate(row):
            key = row.keys()[index]
            if include_extras or key in object.__dict__:
                object.__dict__[key] = value
    return object
    
def insert_generic_into_db(object, filename, table_name, ignore_list=[], replace_into=False):
    keys = []
    values = []
    columns_str = None
    values_str = None
    for key, value in vars(object).items():
        if not key in ignore_list:
            keys.append(key)
            values.append(value)
            if columns_str:
                columns_str = "{0},[{1}]".format(columns_str, key)
            else:
                columns_str = "[{0}]".format(key)
            if values_str:
                values_str = values_str + ",?"
            else:
                values_str = "?"
    query = "INSERT{0} INTO [{1}] ({2}) VALUES ({3})".format(" OR REPLACE" if replace_into else "", table_name, columns_str, values_str)
    db_execute(filename, query, values)
    
def update_generic_in_db(object, filename, table_name, id_column="id", id_value=None, ignore_list=[]):
    if not id_value:
        id_value = object.id
    keys = []
    values = []
    set_str = None
    for key, value in vars(object).items():
        if not key in ignore_list:
            keys.append(key)
            values.append(value)
            if set_str:
                set_str = "{0},[{1}]=?".format(set_str, key)
            else:
                set_str = "[{0}]=?".format(key)
    query = "UPDATE [{0}] SET {1} WHERE [{2}]={3}".format(table_name, set_str, id_column, id_value)
    db_execute(filename, query, values)

def db_execute(filename, query, values):
    conn = sqlite3.connect(filename)
    cursor = conn.cursor()
    try:
        cursor.execute(query, values)
    except:
        print 'Error executing on database:'
        print '"{0}"'.format(query)
        print values
    finally:
        conn.commit()
        cursor.close()   
    
def munge(string):
    return unicode(string).encode('utf-8', 'xmlcharrefreplace')
    
    