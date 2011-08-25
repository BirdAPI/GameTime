"""Wrapper for mod_python, for use as a CherryPy HTTP server.

To autostart modpython, the "apache" executable or script must be
on your system path, or you must override the global APACHE_PATH.
On some platforms, "apache" may be called "apachectl" or "apache2ctl"--
create a symlink to them if needed.

You also need the 'modpython_gateway' module at:
http://projects.amor.org/misc/wiki/ModPythonGateway


KNOWN BUGS
==========

1. Apache processes Range headers automatically; CherryPy's truncated
    output is then truncated again by Apache. See test_core.testRanges.
    This was worked around in http://www.cherrypy.org/changeset/1319.
2. Apache does not allow custom HTTP methods like CONNECT as per the spec.
    See test_core.testHTTPMethods.
3. Max request header and body settings do not work with Apache.
4. Apache replaces status "reason phrases" automatically. For example,
    CherryPy may set "304 Not modified" but Apache will write out
    "304 Not Modified" (capital "M").
5. Apache does not allow custom error codes as per the spec.
6. Apache (or perhaps modpython, or modpython_gateway) unquotes %xx in the
    Request-URI too early.
"""

import os
curdir = os.path.join(os.getcwd(), os.path.dirname(__file__))
import re
import time

import test


def read_process(cmd, args=""):
    pipein, pipeout = os.popen4("%s %s" % (cmd, args))
    try:
        firstline = pipeout.readline()
        if (re.search(r"(not recognized|No such file|not found)", firstline,
                      re.IGNORECASE)):
            raise IOError('%s must be on your system path.' % cmd)
        output = firstline + pipeout.read()
    finally:
        pipeout.close()
    return output


APACHE_PATH = "apache"
CONF_PATH = "test_mp.conf"
ready = False
interrupt = None

conf_template = """
# Apache2 server configuration file for testing CherryPy with mod_python.

DocumentRoot "/"
Listen %s
LoadModule python_module modules/mod_python.so

SetHandler python-program
PythonFixupHandler cherrypy.test.modpy::handler
PythonOption testmod %s
PythonHandler modpython_gateway::handler
PythonOption wsgi.application cherrypy._cpwsgi::wsgiApp
PythonDebug On
"""

def start(testmod, port):
    mpconf = CONF_PATH
    if not os.path.isabs(mpconf):
        mpconf = os.path.join(curdir, mpconf)
    
    f = open(mpconf, 'wb')
    try:
        f.write(conf_template % (port, testmod))
    finally:
        f.close()
    
    result = read_process(APACHE_PATH, "-k start -f %s" % mpconf)
    if result:
        print result

def stop():
    """Gracefully shutdown a server that is serving forever."""
    read_process(APACHE_PATH, "-k stop")


loaded = False

def handler(req):
    global loaded
    if not loaded:
        loaded = True
        options = req.get_options()
        testmod = options.get('testmod')
        m = __import__(('cherrypy.test.%s' % testmod), globals(), locals(), [''])
        import cherrypy
        cherrypy.config.update({
            "server.log_file": os.path.join(curdir, "test.log"),
            "server.environment": "production",
            })
        m.setup_server()
        cherrypy.server.start(init_only=True, server_class=None, server=None)
    from mod_python import apache
    return apache.OK


class ModPythonTestHarness(test.TestHarness):
    """TestHarness for ModPython and CherryPy."""
    
    def _run(self, conf):
        import webtest
        webtest.WebCase.PORT = self.port
        webtest.WebCase.interactive = self.interactive
        print
        print "Running tests:", self.server
        
        # mod_python, since it runs in the Apache process, must be
        # started separately for each test, and then *that* process
        # must run the setup_server() function for the test.
        # Then our process can run the actual test.
        test_success = True
        for testmod in self.tests:
            try:
                start(testmod, self.port)
                suite = webtest.ReloadingTestLoader().loadTestsFromName(testmod)
                result = webtest.TerseTestRunner(verbosity=2).run(suite)
                test_success &= result.wasSuccessful()
            finally:
                stop()
        if test_success:
            return 0
        else:
            return 1


