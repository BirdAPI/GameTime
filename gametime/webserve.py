#!/usr/bin/python

class WebInterface:

    @cherrypy.expose
    def index(self):
        print "Welcome to GameTime!"
    