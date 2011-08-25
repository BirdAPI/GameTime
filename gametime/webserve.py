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
        print iso
    
def munge(string):
    return unicode(string).encode('utf-8', 'xmlcharrefreplace')