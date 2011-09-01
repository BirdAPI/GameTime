#!/usr/bin/python

import cherrypy.lib

import sys
import re
import os

import gametime

from cheetah.Template import Template

from abgx360 import abgx360
from IGN import ign
from IGN.ign import IGN

class WebInterface:

    @cherrypy.expose
    def index(self):
        print "Welcome to GameTime!"
        t = Template(open(os.path.join(gametime.TMPL_DIR, "index.tmpl")).read())
        return munge(t)
    
    @cherrypy.expose
    def search(self, query):
        t = Template(open(os.path.join(gametime.TMPL_DIR, "search.tmpl")).read())
        t.results = IGN.search(query)
        return munge(t)
        
    @cherrypy.expose
    def addGame(self, ign_id):
        return None
        
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