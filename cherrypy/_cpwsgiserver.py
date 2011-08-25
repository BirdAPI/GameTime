"""A high-speed, production ready, thread pooled, generic WSGI server."""

import mimetools # todo: use email
import Queue
import re
quoted_slash = re.compile("(?i)%2F")
import rfc822
import socket
import sys
import threading
import time
import traceback
from urllib import unquote
from urlparse import urlparse

import errno
socket_errors_to_ignore = []
# Not all of these names will be defined for every platform.
for _ in ("EPIPE", "ETIMEDOUT", "ECONNREFUSED", "ECONNRESET",
          "EHOSTDOWN", "EHOSTUNREACH",
          "WSAECONNABORTED", "WSAECONNREFUSED", "WSAECONNRESET",
          "WSAENETRESET", "WSAETIMEDOUT"):
    if _ in dir(errno):
        socket_errors_to_ignore.append(getattr(errno, _))
# de-dupe the list
socket_errors_to_ignore = dict.fromkeys(socket_errors_to_ignore).keys()

# These are lowercase because mimetools.Message uses lowercase keys.
comma_separated_headers = [
    'accept', 'accept-charset', 'accept-encoding', 'accept-language',
    'accept-ranges', 'allow', 'cache-control', 'connection', 'content-encoding',
    'content-language', 'expect', 'if-match', 'if-none-match', 'pragma',
    'proxy-authenticate', 'te', 'trailer', 'transfer-encoding', 'upgrade',
    'vary', 'via', 'warning', 'www-authenticate',
    ]

class HTTPRequest(object):
    
    stderr = sys.stderr
    bufsize = -1
    
    def __init__(self, socket, addr, server):
        self.socket = socket
        self.addr = addr
        self.server = server
        self.environ = {}
        self.ready = False
        self.started_response = False
        self.status = ""
        self.outheaders = []
        self.outheaderkeys = []
        self.rfile = self.socket.makefile("r", self.bufsize)
        self.wfile = self.socket.makefile("w", self.bufsize)
        self.sent_headers = False
    
    def parse_request(self):
        self.sent_headers = False
        self.environ = {}
        self.environ["wsgi.version"] = (1,0)
        self.environ["wsgi.url_scheme"] = "http"
        self.environ["wsgi.input"] = self.rfile
        self.environ["wsgi.errors"] = self.stderr
        self.environ["wsgi.multithread"] = True
        self.environ["wsgi.multiprocess"] = False
        self.environ["wsgi.run_once"] = False
        request_line = self.rfile.readline()
        if not request_line:
            self.ready = False
            return
        
        if request_line == "\r\n":
            # RFC 2616 sec 4.1: "...if the server is reading the protocol
            # stream at the beginning of a message and receives a CRLF
            # first, it should ignore the CRLF."
            # But only ignore one leading line! else we enable a DoS.
            request_line = self.rfile.readline()
            if not request_line:
                self.ready = False
                return
        
        method, path, req_protocol = request_line.strip().split(" ", 2)
        self.environ["REQUEST_METHOD"] = method
        
        # path may be an abs_path (including "http://host.domain.tld");
        scheme, location, path, params, qs, frag = urlparse(path)
        if scheme:
            self.environ["wsgi.url_scheme"] = scheme
        if params:
            path = path + ";" + params
        
        # Unquote the path+params (e.g. "/this%20path" -> "this path").
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html#sec5.1.2
        #
        # But note that "...a URI must be separated into its components
        # before the escaped characters within those components can be
        # safely decoded." http://www.ietf.org/rfc/rfc2396.txt, sec 2.4.2
        atoms = [unquote(x) for x in quoted_slash.split(path)]
        path = "%2F".join(atoms)
        
        for mount_point, wsgi_app in self.server.mount_points:
            if path == "*":
                # This means, of course, that the first wsgi_app will
                # always handle a URI of "*".
                self.environ["SCRIPT_NAME"] = ""
                self.environ["PATH_INFO"] = "*"
                self.wsgi_app = wsgi_app
                break
            # The mount_points list should be sorted by length, descending.
            if path.startswith(mount_point):
                self.environ["SCRIPT_NAME"] = mount_point
                self.environ["PATH_INFO"] = path[len(mount_point):]
                self.wsgi_app = wsgi_app
                break
        else:
            self.abort("404 Not Found")
            return
        
        # Note that, like wsgiref and most other WSGI servers,
        # we unquote the path but not the query string.
        self.environ["QUERY_STRING"] = qs
        self.environ["SERVER_PROTOCOL"] = req_protocol
        # If the Request-URI was an absoluteURI, use its location atom.
        self.environ["SERVER_NAME"] = location or self.server.server_name
        
        if isinstance(self.server.bind_addr, basestring):
            # AF_UNIX. This isn't really allowed by WSGI, which doesn't
            # address unix domain sockets. But it's better than nothing.
            self.environ["SERVER_PORT"] = ""
        else:
            self.environ["SERVER_PORT"] = str(self.server.bind_addr[1])
            # optional values
            # Until we do DNS lookups, don't include REMOTE_HOST
            self.environ["REMOTE_ADDR"] = self.addr[0]
            self.environ["REMOTE_PORT"] = str(self.addr[1])
        
        # then all the http headers
        headers = mimetools.Message(self.rfile)
        self.environ["CONTENT_TYPE"] = headers.getheader("Content-type", "")
        cl = headers.getheader("Content-length")
        if method in ("POST", "PUT") and cl is None:
            # No Content-Length header supplied. This will hang
            # cgi.FieldStorage, since it cannot determine when to
            # stop reading from the socket. Until we handle chunked
            # encoding, always respond with 411 Length Required.
            # See http://www.cherrypy.org/ticket/493.
            self.abort("411 Length Required")
            return
        self.environ["CONTENT_LENGTH"] = cl or ""
        
        for k in headers:
            envname = "HTTP_" + k.upper().replace("-", "_")
            if k in comma_separated_headers:
                self.environ[envname] = ", ".join(headers.getheaders(k))
            else:
                self.environ[envname] = headers[k]
        self.ready = True
    
    def abort(self, status, msg=""):
        """Write a simple error message back to the client."""
        proto = self.environ.get("SERVER_PROTOCOL", "HTTP/1.0")
        self.wfile.write("%s %s\r\n" % (proto, status))
        self.wfile.write("Content-Length: %s\r\n\r\n" % len(msg))
        if msg:
            self.wfile.write(msg)
        self.wfile.flush()
        self.ready = False
    
    def start_response(self, status, headers, exc_info = None):
        if self.started_response:
            if not exc_info:
                assert False, "Already started response"
            else:
                try:
                    raise exc_info[0], exc_info[1], exc_info[2]
                finally:
                    exc_info = None
        self.started_response = True
        self.status = status
        self.outheaders = headers
        self.outheaderkeys = [key.lower() for (key,value) in self.outheaders]
        return self.write
    
    def write(self, d):
        if not self.sent_headers:
            self.sent_headers = True
            self.send_headers()
        self.wfile.write(d)
        self.wfile.flush()
    
    def send_headers(self):
        if "content-length" not in self.outheaderkeys:
            self.close_at_end = True
        if "date" not in self.outheaderkeys:
            self.outheaders.append(("Date", rfc822.formatdate()))
        if "server" not in self.outheaderkeys:
            self.outheaders.append(("Server", self.server.version))
        if (self.environ["SERVER_PROTOCOL"] == "HTTP/1.1"
            and "connection" not in self.outheaderkeys):
            self.outheaders.append(("Connection", "close"))
        self.wfile.write(self.environ["SERVER_PROTOCOL"] + " " + self.status + "\r\n")
        for (k,v) in self.outheaders:
            self.wfile.write(k + ": " + v + "\r\n")
        self.wfile.write("\r\n")
        self.wfile.flush()
    
    def terminate(self):
        if self.ready and not self.sent_headers and not self.server.interrupt:
            self.sent_headers = True
            self.send_headers()
        self.rfile.close()
        self.wfile.close()
        self.socket.close()


_SHUTDOWNREQUEST = None

class WorkerThread(threading.Thread):
    
    def __init__(self, server):
        self.ready = False
        self.server = server
        threading.Thread.__init__(self)
    
    def run(self):
        try:
            self.ready = True
            while True:
                request = self.server.requests.get()
                if request is _SHUTDOWNREQUEST:
                    return
                
                try:
                    try:
                        request.parse_request()
                        if request.ready:
                            response = request.wsgi_app(request.environ,
                                                        request.start_response)
                            try:
                                for line in response:
                                    request.write(line)
                            finally:
                                if hasattr(response, "close"):
                                    response.close()
                    except socket.error, e:
                        errno = e.args[0]
                        if errno not in socket_errors_to_ignore:
                            traceback.print_exc()
                    except (KeyboardInterrupt, SystemExit), exc:
                        self.server.interrupt = exc
                    except:
                        traceback.print_exc()
                finally:
                    request.terminate()
        except (KeyboardInterrupt, SystemExit), exc:
            self.server.interrupt = exc


class CherryPyWSGIServer(object):
    """An HTTP server for WSGI.
    
    bind_addr: a (host, port) tuple if TCP sockets are desired;
        for UNIX sockets, supply the filename as a string.
    wsgi_app: the WSGI 'application callable'; multiple WSGI applications
        may be passed as (script_name, callable) pairs.
    numthreads: the number of worker threads to create (default 10).
    server_name: the string to set for WSGI's SERVER_NAME environ entry.
        Defaults to socket.gethostname().
    max: the maximum number of queued requests (defaults to -1 = no limit).
    request_queue_size: the 'backlog' argument to socket.listen();
        specifies the maximum number of queued connections (default 5).
    timeout: the timeout in seconds for accepted connections (default 10).
    """
    
    version = "CherryPy/2.3.0"
    protocol = "HTTP/1.0"
    ready = False
    interrupt = None
    RequestHandlerClass = HTTPRequest
    
    def __init__(self, bind_addr, wsgi_app, numthreads=10, server_name=None,
                 max=-1, request_queue_size=5, timeout=10):
        self.requests = Queue.Queue(max)
        
        if callable(wsgi_app):
            # We've been handed a single wsgi_app, in CP-2.1 style.
            # Assume it's mounted at "".
            self.mount_points = [("", wsgi_app)]
        else:
            # We've been handed a list of (mount_point, wsgi_app) tuples,
            # so that the server can call different wsgi_apps, and also
            # correctly set SCRIPT_NAME.
            self.mount_points = wsgi_app
        self.mount_points.sort()
        self.mount_points.reverse()
        
        self.bind_addr = bind_addr
        self.numthreads = numthreads or 1
        if not server_name:
            server_name = socket.gethostname()
        self.server_name = server_name
        self.request_queue_size = request_queue_size
        self._workerThreads = []
        
        self.timeout = timeout
    
    def start(self):
        """Run the server forever."""
        # We don't have to trap KeyboardInterrupt or SystemExit here,
        # because cherrpy.server already does so, calling self.stop() for us.
        # If you're using this server with another framework, you should
        # trap those exceptions in whatever code block calls start().
        
        def bind(family, type, proto=0):
            """Create (or recreate) the actual socket object."""
            self.socket = socket.socket(family, type, proto)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(self.bind_addr)
        
        # Select the appropriate socket
        if isinstance(self.bind_addr, basestring):
            # AF_UNIX socket
            
            # So we can reuse the socket...
            try: os.unlink(self.bind_addr)
            except: pass
            
            # So everyone can access the socket...
            try: os.chmod(self.bind_addr, 0777)
            except: pass
            
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(self.bind_addr)
        else:
            # AF_INET or AF_INET6 socket
            # Get the correct address family for our host (allows IPv6 addresses)
            host, port = self.bind_addr
            flags = 0
            if host == '':
                # Despite the socket module docs, using '' does not
                # allow AI_PASSIVE to work. Passing None instead
                # returns '0.0.0.0' like we want.
                host = None
                flags = socket.AI_PASSIVE
            try:
                info = socket.getaddrinfo(host, port, socket.AF_UNSPEC,
                                          socket.SOCK_STREAM, 0, flags)
            except socket.gaierror:
                # Probably a DNS issue. Assume IPv4.
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.socket.bind(self.bind_addr)
            else:
                self.socket = None
                msg = "No socket could be created"
                for res in info:
                    af, socktype, proto, canonname, sa = res
                    try:
                        self.socket = socket.socket(af, socktype, proto)
                        self.socket.setsockopt(socket.SOL_SOCKET,
                                               socket.SO_REUSEADDR, 1)
                        self.socket.bind(self.bind_addr)
                    except socket.error, msg:
                        if self.socket:
                            self.socket.close()
                        self.socket = None
                        continue
                    break
                if not self.socket:
                    raise socket.error, msg
        
        # Timeout so KeyboardInterrupt can be caught on Win32
        self.socket.settimeout(1)
        self.socket.listen(self.request_queue_size)
        
        # Create worker threads
        for i in xrange(self.numthreads):
            self._workerThreads.append(WorkerThread(self))
        for worker in self._workerThreads:
            worker.setName("CP WSGIServer " + worker.getName())
            worker.start()
        for worker in self._workerThreads:
            while not worker.ready:
                time.sleep(.1)
        
        self.ready = True
        while self.ready:
            self.tick()
            if self.interrupt:
                raise self.interrupt
    
    def tick(self):
        try:
            s, addr = self.socket.accept()
            if not self.ready:
                return
            if hasattr(s, 'settimeout'):
                s.settimeout(self.timeout)
            request = self.RequestHandlerClass(s, addr, self)
            self.requests.put(request)
        except socket.timeout:
            # The only reason for the timeout in start() is so we can
            # notice keyboard interrupts on Win32, which don't interrupt
            # accept() by default
            return
        except socket.error, x:
            msg = x.args[1]
            if msg == "Bad file descriptor":
                # Our socket was closed
                return
            if msg == "Resource temporarily unavailable":
                # Just try again. See http://www.cherrypy.org/ticket/479.
                return
            raise
    
    def stop(self):
        """Gracefully shutdown a server that is serving forever."""
        self.ready = False
        s = getattr(self, "socket", None)
        if s and hasattr(s, "close"):
            s.close()
        
        # Must shut down threads here so the code that calls
        # this method can know when all threads are stopped.
        for worker in self._workerThreads:
            self.requests.put(_SHUTDOWNREQUEST)
        
        # Don't join currentThread (when stop is called inside a request).
        current = threading.currentThread()
        while self._workerThreads:
            worker = self._workerThreads.pop()
            if worker is not current and worker.isAlive:
                try:
                    worker.join()
                except AssertionError:
                    pass


