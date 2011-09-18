#!/usr/bin/python

import cherrypy.lib.auth_basic
import os

import shutil

import gametime
from gametime import logger
from gametime.webserve import WebInterface

def initWebServer(options = {}):
        options.setdefault('port',      8083)
        options.setdefault('host',      '0.0.0.0')
        options.setdefault('log_dir',   None)
        options.setdefault('username',    '')
        options.setdefault('password',    '')
        options.setdefault('web_root',   '/')
        options.setdefault('data_root',   os.path.join(os.getcwd(), 'data'))
        assert isinstance(options['port'], int)
        assert 'data_root' in options

        # cherrypy setup
        cherrypy.config.update({
                'server.socket_port': options['port'],
                'server.socket_host': options['host'],
                'log.screen':         False,
        })

        #HTTP Errors
        def http_error_401_hander(status, message, traceback, version):
            args = [status, message, traceback, version]
            if int(status) == 401:
                logger.log(u"Authentication error, check cherrypy log for more details", logger.WARNING)
            else:
                logger.log(u"CherryPy caught an error: %s %s" % (status, message), logger.ERROR)
                logger.log(traceback, logger.DEBUG)
            return "<html><body><h1>Error %s</h1>Something unexpected has happened. Please check the log.</body></html>" % args[0]
        cherrypy.config.update({'error_page.401' : http_error_401_hander})

        # setup cherrypy logging
        if options['log_dir'] and os.path.isdir(options['log_dir']):
                cherrypy.config.update({ 'log.access_file': os.path.join(options['log_dir'], "cherrypy.log") })
                logger.log('Using %s for cherrypy log' % cherrypy.config['log.access_file'])

        conf = {
                        '/': {
                                'tools.staticdir.root': options['data_root'],
                                'tools.encode.on': True,
                                'tools.encode.encoding': 'utf-8',
                        },
                        '/images': {
                                'tools.staticdir.on':  True,
                                'tools.staticdir.dir': 'images'
                        },
                        '/js':     {
                                'tools.staticdir.on':  True,
                                'tools.staticdir.dir': 'js'
                        },
                        '/css':    {
                                'tools.staticdir.on':  True,
                                'tools.staticdir.dir': 'css'
                        },
        }
        app = cherrypy.tree.mount(WebInterface(), options['web_root'], conf)

        # auth
        if options['username'] != "" and options['password'] != "":
                checkpassword = cherrypy.lib.auth_basic.checkpassword_dict({options['username']: options['password']})
                app.merge({
                        '/': {
                                'tools.auth_basic.on':            True,
                                'tools.auth_basic.realm':         'GameTime',
                                'tools.auth_basic.checkpassword': checkpassword
                        }
                })

        if not os.path.exists(gametime.DATABASE_FILENAME):
            try:
                shutil.copy(gametime.DATABASE_SCHEMA_FILENAME, gametime.DATABASE_FILENAME)
            except IOError:
                print "Error copying %s to %s" % (gametime.DATABASE_SCHEMA_FILENAME, gametime.DATABASE_FILENAME)
                
        cherrypy.server.start()
        cherrypy.server.wait()
