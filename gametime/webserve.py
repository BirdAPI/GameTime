#!/usr/bin/python

import cherrypy.lib

import sys
import re
import os

import gametime

from cheetah.Template import Template

from abgx360 import abgx360

class WebInterface:

    @cherrypy.expose
    def index(self):
        print "Welcome to GameTime!"
        
    @cherrypy.expose
    def verifyStealth(self):
        t = Template(open(os.path.join(gametime.TMPL_DIR, "verifyStealth.tmpl")).read())
        return munge(t)
        
    @cherrypy.expose    
    def doVerifyStealth(self, iso):
        t = Template(open(os.path.join(gametime.TMPL_DIR, "doVerifyStealth.tmpl")).read())
        t.iso = iso
        return munge(t)
        
        (xex, ss_filename, dmi_filename) = abgx360.get_xex_game_patches(iso)
        if ss_filename is not None and dmi_filename is not None:
            print "Patching: %s to SSv2..." % iso
            patch_html_log = abgx360.stealth_patch_ssv2(iso, ss_filename, dmi_filename, xex)
            print "Done patching to SSv2."
            patch_success = abgx360.was_patch_successful(patch_html_log)
            if patch_success:
                print "Patching was successful!"
                return munge(open(patch_html_log).read())
    
def munge(string):
    return unicode(string).encode('utf-8', 'xmlcharrefreplace')