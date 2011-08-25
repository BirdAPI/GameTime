#!/usr/bin/python

import cherrypy.lib

class WebInterface:

    @cherrypy.expose
    def index(self):
        print "Welcome to GameTime!"
    