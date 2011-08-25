"""Test the various means of instantiating and invoking filters."""

import time
import types
import test
test.prefer_parent_path()

import cherrypy
from cherrypy import filters
from cherrypy.filters.basefilter import BaseFilter


class AccessFilter(BaseFilter):
    
    def before_request_body(self):
        if not cherrypy.config.get("access_filter.on", False):
            return
        
        if not getattr(cherrypy.request, "login", None):
            raise cherrypy.HTTPError(401)


def setup_server():

    class Numerify(BaseFilter):
        
        def on_start_resource(self):
            m = cherrypy.config.get("numerify_filter.map", {})
            cherrypy.request.numerify_map = m.items()
        
        def before_finalize(self):
            if not cherrypy.config.get("numerify_filter.on", False):
                return
            
            def number_it(body):
                for chunk in body:
                    for k, v in cherrypy.request.numerify_map:
                        chunk = chunk.replace(k, v)
                    yield chunk
            cherrypy.response.body = number_it(cherrypy.response.body)
    
    
    # It's not mandatory to inherit from BaseFilter.
    class NadsatFilter:
        
        def __init__(self):
            self.counter = 0
            self.ended = {}
        
        def before_main(self):
            cherrypy.request.counter = self.counter = self.counter + 1
            self.ended[cherrypy.request.counter] = False
        
        def before_finalize(self):
            def nadsat_it_up(body):
                for chunk in body:
                    chunk = chunk.replace("good", "horrorshow")
                    chunk = chunk.replace("piece", "lomtick")
                    yield chunk
            cherrypy.response.body = nadsat_it_up(cherrypy.response.body)
        
        def on_end_request(self):
            # This runs after the request has been completely written out.
            cherrypy.response.body = "razdrez"
            self.ended[cherrypy.request.counter] = True



    class Root:
        def index(self):
            return "Howdy earth!"
        index.exposed = True

    cherrypy.root = Root()


    class TestType(type):
        """Metaclass which automatically exposes all functions in each subclass,
        and adds an instance of the subclass as an attribute of cherrypy.root.
        """
        def __init__(cls, name, bases, dct):
            type.__init__(name, bases, dct)
            for value in dct.itervalues():
                if isinstance(value, types.FunctionType):
                    value.exposed = True
            setattr(cherrypy.root, name.lower(), cls())
    class Test(object):
        __metaclass__ = TestType


    class CPFilterList(Test):
        
        # METHOD ONE:
        # Use _cp_filters (old name: _cpFilterList)
        _cp_filters = [NadsatFilter()]
        
        def index(self):
            return "A good piece of cherry pie"
        
        def ended(self, id):
            return repr(self._cp_filters[0].ended[int(id)])
        
        def err(self):
            raise ValueError()
        
        def stream(self):
            for i in xrange(100000000):
                yield str(i)
        
        def errinstream(self):
            raise ValueError()
            yield "confidential"
        
        def restricted(self):
            return "Welcome!"
        
        def err_in_onstart(self):
            return "success!"


    cherrypy.config.update({
        'global': {
            # METHOD TWO:
            # Declare a classname in server.input_filters.
            'server.input_filters': ["cherrypy.test.test_custom_filters.AccessFilter"],
            'server.log_to_screen': False,
            'server.environment': 'production',
            'server.show_tracebacks': True,
        },
        '/cpfilterlist': {
            'numerify_filter.on': True,
            'numerify_filter.map': {"pie": "3.14159"}
        },
        '/cpfilterlist/restricted': {
            'access_filter.on': True,
            'server.show_tracebacks': False,
        },
        '/cpfilterlist/errinstream': {
            'stream_response': True,
        },
        '/cpfilterlist/stream': {
            'stream_response': True,
        },
        '/cpfilterlist/err_in_onstart': {
            # Because this isn't a dict, on_start_resource will error.
            'numerify_filter.map': "pie->3.14159"
        },
    })

    # METHOD THREE:
    # Insert a class directly into the filters.output_filters chain.
    # You can also insert a string, but we're effectively testing
    # using-a-string via the config file.
    filters.input_filters.insert(0, Numerify)
    filters.output_filters.insert(0, Numerify)

    # We have to call filters.init() here (if we want methods #2 and #3
    # to work), because the test suite may already have run server.start()
    # (which is where filters.init() is usually called).
    filters.init()


#                             Client-side code                             #

import helper


class FilterTests(helper.CPWebCase):
    def testCPFilterList(self):
        self.getPage("/cpfilterlist/")
        # If body is "razdrez", then on_end_request is being called too early.
        self.assertBody("A horrorshow lomtick of cherry 3.14159")
        # If this fails, then on_end_request isn't being called at all.
        self.getPage("/cpfilterlist/ended/1")
        self.assertBody("True")
        
        valerr = '\n    raise ValueError()\nValueError'
        self.getPage("/cpfilterlist/err")
        # If body is "razdrez", then on_end_request is being called too early.
        self.assertErrorPage(500, pattern=valerr)
        # If this fails, then on_end_request isn't being called at all.
        self.getPage("/cpfilterlist/ended/3")
        self.assertBody("True")
        
        # If body is "razdrez", then on_end_request is being called too early.
        self.getPage("/cpfilterlist/errinstream")
        # Because this error is raised after the response body has
        # started, the status should not change to an error status.
        self.assertStatus("200 OK")
        self.assertBody("Unrecoverable error in the server.")
        # If this fails, then on_end_request isn't being called at all.
        self.getPage("/cpfilterlist/ended/5")
        self.assertBody("True")

        # Test that on_end_request is called even if the client drops.
        self.persistent = True
        try:
            conn = self.HTTP_CONN
            conn.putrequest('GET', '/cpfilterlist/stream', skip_host=True)
            conn.putheader('Host', self.HOST)
            conn.endheaders()
            # Skip the rest of the request and close the conn. This will 
            # cause the server's active socket to error, which *should* 
            # result in the request being aborted, and request.close being 
            # called all the way up the stack (including WSGI middleware), 
            # eventually calling our on_end_request hook.
        finally:
            self.persistent = False
        time.sleep(0.1)
        # on_end_request should have been called
        self.getPage('/cpfilterlist/ended/7')
        self.assertBody("True")
        
        # Test the config method.
        self.getPage("/cpfilterlist/restricted")
        self.assertErrorPage(401)
    
    def testGuaranteedFilters(self):
        # The on_start_resource and on_end_request filter methods are all
        # guaranteed to run, even if there are failures in other on_start
        # or on_end methods. This is NOT true of the other filter methods.
        # Here, we have set up a failure in NumerifyFilter.on_start_resource,
        # but because that failure is logged and passed over, the error
        # page we obtain in the user agent should be from before_finalize.
        self.getPage("/cpfilterlist/err_in_onstart")
        self.assertErrorPage(500)
        self.assertInBody("AttributeError: 'Request' object has no "
                          "attribute 'numerify_map'")


if __name__ == '__main__':
    setup_server()
    helper.testmain()

