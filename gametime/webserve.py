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

from abgx360 import abgx360
from mydate import MyDate
from mygame import MyGame
import providers
from providers import providers, GAME_PROVIDERS

class WebInterface:

    @cherrypy.expose
    def index(self):
        t = Template(open(os.path.join(gametime.TMPL_DIR, "index.tmpl")).read())
        mygames = MyGame.get_all()
        mygames = sorted(mygames, key=lambda g: (g.my_date, g.title))
        t.mygames = mygames
        return munge(t)
    
    @cherrypy.expose
    def search(self, query, site_id):
        if site_id in GAME_PROVIDERS:
            provider = GAME_PROVIDERS[site_id]
            t = Template(open(os.path.join(gametime.TMPL_DIR, provider.search_tmpl)).read())
            t.results = provider.search(query)
            t.site_id = site_id
            return munge(t)
        return None
    
    @cherrypy.expose
    def gameInfo(self, id):
        game = MyGame.get(id)
        t = Template(open(os.path.join(gametime.TMPL_DIR, "gameInfo.tmpl")).read())
        t.game = game

        for provider in GAME_PROVIDERS.values():
            t.__dict__[provider.site_id] = provider.get_one(game.get_provider_id(provider))
            
        return munge(t)
    
    @cherrypy.expose
    def addGame(self, title, system, info_id, site_id):
        game = MyGame()
        game.title = title
        game.system = providers.normalize_system(system)
        if site_id in GAME_PROVIDERS:
            provider = GAME_PROVIDERS[site_id]
            game.set_provider_id(provider, info_id)
            game.insert_in_db()
            self.updateInfo(game.id, site_id, info_id, False)
        raise cherrypy.HTTPRedirect("/#Game_{0}".format(game.id))
    
    @cherrypy.expose
    def removeGame(self, id):
        MyGame.delete_from_db(id)
        raise cherrypy.HTTPRedirect("/")
    
    @cherrypy.expose
    def updateAllGames(self, redirect=True):
        ids = MyGame.get_all_ids()
        for id in ids:
            self.updateGame(id, False)
        if redirect:
            raise cherrypy.HTTPRedirect("/")
    
    @cherrypy.expose
    def updateGame(self, id, redirect=True):
        game = MyGame.get(id)
        for provider in GAME_PROVIDERS.values():
            self.updateInfo(id, provider.site_id, game.get_provider_id(provider), False)
        if redirect:
            raise cherrypy.HTTPRedirect("/#Game_{0}".format(id))
        
    @cherrypy.expose
    def updateInfo(self, id, site_id, info_id=None, redirect=True):
        if site_id in GAME_PROVIDERS:
            provider = GAME_PROVIDERS[site_id]
            game = MyGame.get(id)
            if game:
                if not info_id:
                    info_id = provider.get_match(game.title, game.system)
                if info_id:
                    info = provider.get_info(game.id, info_id)
                    if info:
                        pprint(vars(info))
                        print ""
                        provider.insert_or_update_in_db(info)
                        game.set_provider_id(provider, info_id)
                        game.update_info(provider, info)
        if redirect:
            raise cherrypy.HTTPRedirect("/#Game_{0}".format(id))
    
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
    
def munge(string):
    return unicode(string).encode('utf-8', 'xmlcharrefreplace')
    
    