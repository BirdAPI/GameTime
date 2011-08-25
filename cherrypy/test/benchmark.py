"""CherryPy Benchmark Tool

    Usage:
        benchmark.py --null --notests --help --modpython --ab=path --apache=path
    
    --null:        use a null Request object (to bench the HTTP server only)
    --notests:     start the server but don't run the tests; this allows
                   you to check the tested pages with a browser
    --help:        show this help message
    --modpython:   start up apache on 8080 (with a custom modpython
                   config) and run the tests
    --ab=path:     Use the ab script/executable at 'path' (see below)
    --apache=path: Use the apache script/exe at 'path' (see below)
    
    To run the benchmarks, the Apache Benchmark tool "ab" must either be on
    your system path, or specified via the --ab=path option.
    
    To run the modpython tests, the "apache" executable or script must be
    on your system path, or provided via the --apache=path option. On some
    platforms, "apache" may be called "apachectl" or "apache2ctl"--create
    a symlink to them if needed.
"""

import getopt
import os
curdir = os.path.join(os.getcwd(), os.path.dirname(__file__))

import re
import sys
import time
import traceback

import cherrypy
from cherrypy.lib import httptools


AB_PATH = ""
APACHE_PATH = ""
MOUNT_POINT = "/cpbench/users/rdelon/apps/blog"

__all__ = ['ABSession', 'Root', 'print_report', 'read_process',
           'run_standard_benchmarks', 'safe_threads',
           'size_report', 'startup', 'thread_report',
           ]

size_cache = {}

class Root:
    def index(self):
        return "Hello, world\r\n"
    index.exposed = True
    
    def sizer(self, size):
        resp = size_cache.get(size, None)
        if resp is None:
            size_cache[size] = resp = "X" * int(size)
        return resp
    sizer.exposed = True


conf = {
    'global': {
        'server.log_to_screen': False,
##        'server.log_file': os.path.join(curdir, "bench.log"),
        'server.environment': 'production',
        'server.socket_host': 'localhost',
        'server.socket_port': 8080,
        'server.max_request_header_size': 0,
        'server.max_request_body_size': 0,
        },
    '/static': {
        'static_filter.on': True,
        'static_filter.dir': 'static',
        'static_filter.root': curdir,
        },
    }
cherrypy.tree.mount(Root(), MOUNT_POINT, conf)
cherrypy.lowercase_api = True


class NullRequest:
    """A null HTTP request class, returning 204 and an empty body."""
    
    def __init__(self, remoteAddr, remotePort, remoteHost, scheme="http"):
        pass
    
    def close(self):
        pass
    
    def run(self, requestLine, headers, rfile):
        cherrypy.response.status = "204 No Content"
        cherrypy.response.header_list = [("Content-Type", 'text/html'),
                                         ("Server", "Null CherryPy"),
                                         ("Date", httptools.HTTPDate()),
                                         ("Content-Length", "0"),
                                         ]
        cherrypy.response.body = [""]
        return cherrypy.response


class NullResponse:
    pass


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


class ABSession:
    """A session of 'ab', the Apache HTTP server benchmarking tool.

Example output from ab:

This is ApacheBench, Version 2.0.40-dev <$Revision: 1.121.2.1 $> apache-2.0
Copyright (c) 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
Copyright (c) 1998-2002 The Apache Software Foundation, http://www.apache.org/

Benchmarking localhost (be patient)
Completed 100 requests
Completed 200 requests
Completed 300 requests
Completed 400 requests
Completed 500 requests
Completed 600 requests
Completed 700 requests
Completed 800 requests
Completed 900 requests


Server Software:        CherryPy/2.2.0beta
Server Hostname:        localhost
Server Port:            8080

Document Path:          /static/index.html
Document Length:        14 bytes

Concurrency Level:      10
Time taken for tests:   9.643867 seconds
Complete requests:      1000
Failed requests:        0
Write errors:           0
Total transferred:      189000 bytes
HTML transferred:       14000 bytes
Requests per second:    103.69 [#/sec] (mean)
Time per request:       96.439 [ms] (mean)
Time per request:       9.644 [ms] (mean, across all concurrent requests)
Transfer rate:          19.08 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    0   2.9      0      10
Processing:    20   94   7.3     90     130
Waiting:        0   43  28.1     40     100
Total:         20   95   7.3    100     130

Percentage of the requests served within a certain time (ms)
  50%    100
  66%    100
  75%    100
  80%    100
  90%    100
  95%    100
  98%    100
  99%    110
 100%    130 (longest request)
Finished 1000 requests
"""
    
    parse_patterns = [('complete_requests', 'Completed',
                       r'^Complete requests:\s*(\d+)'),
                      ('failed_requests', 'Failed',
                       r'^Failed requests:\s*(\d+)'),
                      ('requests_per_second', 'req/sec',
                       r'^Requests per second:\s*([0-9.]+)'),
                      ('time_per_request_concurrent', 'msec/req',
                       r'^Time per request:\s*([0-9.]+).*concurrent requests\)$'),
                      ('transfer_rate', 'KB/sec',
                       r'^Transfer rate:\s*([0-9.]+)'),
                      ]
    
    def __init__(self, path=MOUNT_POINT + "/", requests=1000, concurrency=10):
        self.path = path
        self.requests = requests
        self.concurrency = concurrency
    
    def args(self):
        port = cherrypy.config.get('server.socket_port')
        assert self.concurrency > 0
        assert self.requests > 0
        return ("-n %s -c %s http://localhost:%s%s" %
                (self.requests, self.concurrency, port, self.path))
    
    def run(self):
        # Parse output of ab, setting attributes on self
        self.output = read_process(AB_PATH or "ab", self.args())
        for attr, name, pattern in self.parse_patterns:
            val = re.search(pattern, self.output, re.MULTILINE)
            if val:
                val = val.group(1)
                setattr(self, attr, val)
            else:
                setattr(self, attr, None)


safe_threads = (25, 50, 100, 200, 400)
if sys.platform in ("win32",):
    # For some reason, ab crashes with > 50 threads on my Win2k laptop.
    safe_threads = (10, 20, 30, 40, 50)


def thread_report(path=MOUNT_POINT + "/", concurrency=safe_threads):
    sess = ABSession(path)
    attrs, names, patterns = zip(*sess.parse_patterns)
    rows = [('threads',) + names]
    for c in concurrency:
        sess.concurrency = c
        sess.run()
        rows.append([c] + [getattr(sess, attr) for attr in attrs])
    return rows

def size_report(sizes=(1, 10, 50, 100, 100000, 100000000),
               concurrency=50):
    sess = ABSession(concurrency=concurrency)
    attrs, names, patterns = zip(*sess.parse_patterns)
    rows = [('bytes',) + names]
    for sz in sizes:
        sess.path = "%s/sizer?size=%s" % (MOUNT_POINT, sz)
        sess.run()
        rows.append([sz] + [getattr(sess, attr) for attr in attrs])
    return rows

def print_report(rows):
    widths = []
    for i in range(len(rows[0])):
        lengths = [len(str(row[i])) for row in rows]
        widths.append(max(lengths))
    for row in rows:
        print
        for i, val in enumerate(row):
            print str(val).rjust(widths[i]), "|",
    print


def run_standard_benchmarks():
    print
    print ("Client Thread Report (1000 requests, 14 byte response body, "
           "%s server threads):" % cherrypy.config.get('server.thread_pool'))
    print_report(thread_report())
    
    print
    print ("Client Thread Report (1000 requests, 14 bytes via static_filter, "
           "%s server threads):" % cherrypy.config.get('server.thread_pool'))
    print_report(thread_report("%s/static/index.html" % MOUNT_POINT))
    
    print
    print ("Size Report (1000 requests, 50 client threads, "
           "%s server threads):" % cherrypy.config.get('server.thread_pool'))
    print_report(size_report())


started = False
def startup(req=None):
    """Start the CherryPy app server in 'serverless' mode (for WSGI)."""
    global started
    if not started:
        started = True
        cherrypy.server.start(init_only=True, server_class=None)
    return 0 # apache.OK



#                         modpython and other WSGI                         #

def startup_modpython(req=None):
    """Start the CherryPy app server in 'serverless' mode (for WSGI)."""
    global started
    if not started:
        started = True
        if req.get_options().has_key("nullreq"):
            cherrypy.server.request_class = NullRequest
            cherrypy.server.response_class = NullResponse
        ab_opt = req.get_options().get("ab", "")
        if ab_opt:
            global AB_PATH
            AB_PATH = ab_opt
        cherrypy.server.start(init_only=True, server_class=None)
    
    import modpython_gateway
    return modpython_gateway.handler(req)

mp_conf_template = """
# Apache2 server configuration file for benchmarking CherryPy with mod_python.

DocumentRoot "/"
Listen 8080
LoadModule python_module modules/mod_python.so

<Location />
    SetHandler python-program
    PythonHandler cherrypy.test.benchmark::startup_modpython
    PythonOption application cherrypy._cpwsgi::wsgiApp
    PythonDebug On
%s%s
</Location>
"""

def run_modpython():
    # Pass the null and ab=path options through Apache
    nullreq_opt = ""
    if "--null" in opts:
        nullreq_opt = "    PythonOption nullreq\n"
    
    ab_opt = ""
    if "--ab" in opts:
        ab_opt = "    PythonOption ab %s\n" % opts["--ab"]
    
    conf_data = mp_conf_template % (ab_opt, nullreq_opt)
    mpconf = os.path.join(curdir, "bench_mp.conf")
    
    f = open(mpconf, 'wb')
    try:
        f.write(conf_data)
    finally:
        f.close()
    
    apargs = "-k start -f %s" % mpconf
    try:
        read_process(APACHE_PATH or "apache", apargs)
        run()
    finally:
        os.popen("apache -k stop")



if __name__ == '__main__':
    longopts = ['modpython', 'null', 'notests', 'help', 'ab=', 'apache=']
    try:
        switches, args = getopt.getopt(sys.argv[1:], "", longopts)
        opts = dict(switches)
    except getopt.GetoptError:
        print __doc__
        sys.exit(2)
    
    if "--help" in opts:
        print __doc__
        sys.exit(0)
    
    if "--ab" in opts:
        AB_PATH = opts['--ab']
    
    if "--notests" in opts:
        # Return without stopping the server, so that the pages
        # can be tested from a standard web browser.
        def run():
            if "--null" in opts:
                print "Using null Request object"
    else:
        def run():
            end = time.time() - start
            print "Started in %s seconds" % end
            if "--null" in opts:
                print "\nUsing null Request object"
            try:
                run_standard_benchmarks()
            finally:
                cherrypy.server.stop()
    
    print "Starting CherryPy app server..."
    start = time.time()
    
    if "--modpython" in opts:
        run_modpython()
    else:
        if "--null" in opts:
            cherrypy.server.request_class = NullRequest
            cherrypy.server.response_class = NullResponse
        
        # This will block
        cherrypy.server.start_with_callback(run)
