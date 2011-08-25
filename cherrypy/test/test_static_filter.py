import test
test.prefer_parent_path()

import os
curdir = os.path.join(os.getcwd(), os.path.dirname(__file__))
import threading

import cherrypy
from cherrypy.lib import cptools


def setup_server():
    class Root:
        pass

    class Static:
        
        def index(self):
            return 'You want the Baron? You can have the Baron!'
        index.exposed = True
        
        def dynamic(self):
            return "This is a DYNAMIC page"
        dynamic.exposed = True


    cherrypy.root = Root()
    cherrypy.root.static = Static()

    cherrypy.config.update({
        'global': {
            'static_filter.on': False,
            'server.log_to_screen': False,
            'server.environment': 'production',
        },
        '/static': {
            'static_filter.on': True,
            'static_filter.dir': 'static',
            'static_filter.root': curdir,
        },
        '/style.css': {
            'static_filter.on': True,
            'static_filter.file': 'style.css',
            'static_filter.root': curdir,
        },
        '/docroot': {
            'static_filter.on': True,
            'static_filter.root': curdir,
            'static_filter.dir': 'static',
            'static_filter.index': 'index.html',
        },
        '/error': {
            'static_filter.on': True,
            'server.show_tracebacks': True,
        },
    })

import helper

class StaticFilterTest(helper.CPWebCase):
    
    def testStaticFilter(self):
        self.getPage("/static/index.html")
        self.assertStatus('200 OK')
        self.assertHeader('Content-Type', 'text/html')
        self.assertBody('Hello, world\r\n')
        
        # Using a static_filter.root value in a subdir...
        self.getPage("/docroot/index.html")
        self.assertStatus('200 OK')
        self.assertHeader('Content-Type', 'text/html')
        self.assertBody('Hello, world\r\n')
        
        # Check a filename with spaces in it
        self.getPage("/static/has%20space.html")
        self.assertStatus('200 OK')
        self.assertHeader('Content-Type', 'text/html')
        self.assertBody('Hello, world\r\n')
        
        self.getPage("/style.css")
        self.assertStatus('200 OK')
        self.assertHeader('Content-Type', 'text/css')
        # Note: The body should be exactly 'Dummy stylesheet\n', but
        #   unfortunately some tools such as WinZip sometimes turn \n
        #   into \r\n on Windows when extracting the CherryPy tarball so
        #   we just check the content
        self.assertMatchesBody('^Dummy stylesheet')
        
        # Test that NotFound will then try dynamic handlers (see [878]).
        self.getPage("/static/dynamic")
        self.assertBody("This is a DYNAMIC page")
        
        # Check a directory via fall-through to dynamic handler.
        self.getPage("/static/")
        self.assertStatus('200 OK')
        self.assertHeader('Content-Type', 'text/html')
        self.assertBody('You want the Baron? You can have the Baron!')
        
        # Check a directory via "static_filter.index".
        self.getPage("/docroot/")
        self.assertStatus('200 OK')
        self.assertHeader('Content-Type', 'text/html')
        self.assertBody('Hello, world\r\n')
        # The same page should be returned even if redirected.
        self.getPage("/docroot")
        self.assertStatus('200 OK')
        self.assertHeader('Content-Type', 'text/html')
        self.assertBody('Hello, world\r\n')
        
        # Check that we get a WrongConfigValue error if no .file or .dir
        self.getPage("/error/thing.html")
        self.assertErrorPage(500)
        self.assertInBody("WrongConfigValue: StaticFilter requires either "
                          "static_filter.file or static_filter.dir "
                          "(/error/thing.html)")
        
        # Test up-level security
        self.getPage("/static/../../test/style.css")
        self.assertStatus((400, 403))
        
        # Test modified-since on a reasonably-large file
        self.getPage("/static/dirback.jpg")
        self.assertStatus("200 OK")
        lastmod = ""
        for k, v in self.headers:
            if k == 'Last-Modified':
                lastmod = v
        ims = ("If-Modified-Since", lastmod)
        self.getPage("/static/dirback.jpg", headers=[ims])
        self.assertStatus(304)
        self.assertNoHeader("Content-Type")
        self.assertNoHeader("Content-Length")
        self.assertNoHeader("Content-Disposition")
        self.assertBody("")
        
##        
##        # Test lots of requests for the same file (no If-Mod).
##        ts = []
##        for x in xrange(500):
##            t = threading.Thread(target=self.getPage,
##                                 args=("/static/dirback.jpg",))
##            ts.append(t)
##            t.start()
##        for t in ts:
##            t.join()
##

if __name__ == "__main__":
    setup_server()
    helper.testmain()
