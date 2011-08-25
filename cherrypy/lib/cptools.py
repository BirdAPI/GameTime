"""Tools which both CherryPy and application developers may invoke."""

import md5
import mimetools
import mimetypes
mimetypes.init()
mimetypes.types_map['.dwg']='image/x-dwg'
mimetypes.types_map['.ico']='image/x-icon'

import os
import re
import stat as _stat
import sys
import time

import cherrypy
import httptools

from cherrypy.filters.wsgiappfilter import WSGIAppFilter


def decorate(func, decorator):
    """
    Return the decorated func. This will automatically copy all
    non-standard attributes (like exposed) to the newly decorated function.
    """
    newfunc = decorator(func)
    for key in dir(func):
        if not hasattr(newfunc, key):
            setattr(newfunc, key, getattr(func, key))
    return newfunc

def decorateAll(obj, decorator):
    """
    Recursively decorate all exposed functions of obj and all of its children,
    grandchildren, etc. If you used to use aspects, you might want to look
    into these. This function modifies obj; there is no return value.
    """
    obj_type = type(obj)
    for key in dir(obj):
        # only deal with user-defined attributes
        if hasattr(obj_type, key):
            value = getattr(obj, key)
            if callable(value) and getattr(value, "exposed", False):
                setattr(obj, key, decorate(value, decorator))
            decorateAll(value, decorator)


class ExposeItems:
    """
    Utility class that exposes a getitem-aware object. It does not provide
    index() or default() methods, and it does not expose the individual item
    objects - just the list or dict that contains them. User-specific index()
    and default() methods can be implemented by inheriting from this class.
    
    Use case:
    
    from cherrypy.lib.cptools import ExposeItems
    ...
    cherrypy.root.foo = ExposeItems(mylist)
    cherrypy.root.bar = ExposeItems(mydict)
    """
    exposed = True
    def __init__(self, items):
        self.items = items
    def __getattr__(self, key):
        return self.items[key]


#                     Conditional HTTP request support                     #

def validate_etags(autotags=False):
    """Validate the current ETag against If-Match, If-None-Match headers.
    
    If autotags is True, an ETag response-header value will be provided
    from an MD5 hash of the response body (unless some other code has
    already provided an ETag header). If False (the default), the ETag
    will not be automatic.
    
    WARNING: the autotags feature is not designed for URL's which allow
    methods other than GET. For example, if a POST to the same URL returns
    no content, the automatic ETag will be incorrect, breaking a fundamental
    use for entity tags in a possibly destructive fashion. Likewise, if you
    raise 304 Not Modified, the response body will be empty, the ETag hash
    will be incorrect, and your application will break.
    See http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.24
    """
    response = cherrypy.response
    
    # Guard against being run twice.
    if hasattr(response, "ETag"):
        return
    
    status, reason, msg = httptools.validStatus(response.status)
    
    etag = response.headers.get('ETag')
    
    # Automatic ETag generation. See warning in docstring.
    if (not etag) and autotags:
        if status == 200:
            etag = response.collapse_body()
            etag = '"%s"' % md5.new(etag).hexdigest()
            response.headers['ETag'] = etag
    
    response.ETag = etag
    
    # "If the request would, without the If-Match header field, result in
    # anything other than a 2xx or 412 status, then the If-Match header
    # MUST be ignored."
    if status >= 200 and status <= 299:
        request = cherrypy.request
        
        conditions = request.headers.elements('If-Match') or []
        conditions = [str(x) for x in conditions]
        if conditions and not (conditions == ["*"] or etag in conditions):
            raise cherrypy.HTTPError(412, "If-Match failed: ETag %r did "
                                     "not match %r" % (etag, conditions))
        
        conditions = request.headers.elements('If-None-Match') or []
        conditions = [str(x) for x in conditions]
        if conditions == ["*"] or etag in conditions:
            if request.method in ("GET", "HEAD"):
                raise cherrypy.HTTPRedirect([], 304)
            else:
                raise cherrypy.HTTPError(412, "If-None-Match failed: ETag %r "
                                         "matched %r" % (etag, conditions))

def validate_since():
    """Validate the current Last-Modified against If-Modified-Since headers.
    
    If no code has set the Last-Modified response header, then no validation
    will be performed.
    """
    response = cherrypy.response
    lastmod = response.headers.get('Last-Modified')
    if lastmod:
        status, reason, msg = httptools.validStatus(response.status)
        
        request = cherrypy.request
        
        since = request.headers.get('If-Unmodified-Since')
        if since and since != lastmod:
            if (status >= 200 and status <= 299) or status == 412:
                raise cherrypy.HTTPError(412)
        
        since = request.headers.get('If-Modified-Since')
        if since and since == lastmod:
            if (status >= 200 and status <= 299) or status == 304:
                if request.method in ("GET", "HEAD"):
                    raise cherrypy.HTTPRedirect([], 304)
                else:
                    raise cherrypy.HTTPError(412)


def modified_since(path, stat=None):
    """Check whether a file has been modified since the date
    provided in 'If-Modified-Since'
    It doesn't check if the file exists or not
    Return True if has been modified, False otherwise
    """
    # serveFile already creates a stat object so let's not
    # waste our energy to do it again
    if not stat:
        try:
            stat = os.stat(path)
        except OSError:
            if cherrypy.config.get('server.log_file_not_found', False):
                cherrypy.log("    NOT FOUND file: %s" % path, "DEBUG")
            raise cherrypy.NotFound()
    
    response = cherrypy.response
    strModifTime = httptools.HTTPDate(time.gmtime(stat.st_mtime))
    if cherrypy.request.headers.has_key('If-Modified-Since'):
        if cherrypy.request.headers['If-Modified-Since'] == strModifTime:
            raise cherrypy.HTTPRedirect([], 304)
    response.headers['Last-Modified'] = strModifTime
    return True

def serveFile(path, contentType=None, disposition=None, name=None):
    """Set status, headers, and body in order to serve the given file.
    
    The Content-Type header will be set to the contentType arg, if provided.
    If not provided, the Content-Type will be guessed by its extension.
    
    If disposition is not None, the Content-Disposition header will be set
    to "<disposition>; filename=<name>". If name is None, it will be set
    to the basename of path. If disposition is None, no Content-Disposition
    header will be written.
    """
    
    response = cherrypy.response
    
    # If path is relative, users should fix it by making path absolute.
    # That is, CherryPy should not guess where the application root is.
    # It certainly should *not* use cwd (since CP may be invoked from a
    # variety of paths). If using static_filter, you can make your relative
    # paths become absolute by supplying a value for "static_filter.root".
    if not os.path.isabs(path):
        raise ValueError("'%s' is not an absolute path." % path)
    
    try:
        stat = os.stat(path)
    except OSError:
        if cherrypy.config.get('server.log_file_not_found', False):
            cherrypy.log("    NOT FOUND file: %s" % path, "DEBUG")
        raise cherrypy.NotFound()
    
    # Check if path is a directory.
    if _stat.S_ISDIR(stat.st_mode):
        # Let the caller deal with it as they like.
        raise cherrypy.NotFound()
    
    if contentType is None:
        # Set content-type based on filename extension
        ext = ""
        i = path.rfind('.')
        if i != -1:
            ext = path[i:].lower()
        contentType = mimetypes.types_map.get(ext, "text/plain")
    response.headers['Content-Type'] = contentType
    
    # Set the Last-Modified response header, so that
    # modified-since validation code can work.
    response.headers['Last-Modified'] = httptools.HTTPDate(time.gmtime(stat.st_mtime))
    validate_since()
    
    if disposition is not None:
        if name is None:
            name = os.path.basename(path)
        cd = '%s; filename="%s"' % (disposition, name)
        response.headers["Content-Disposition"] = cd
    
    # Set Content-Length and use an iterable (file object)
    #   this way CP won't load the whole file in memory
    c_len = stat.st_size
    bodyfile = open(path, 'rb')
    if getattr(cherrypy, "debug", None):
        cherrypy.log("    Found file: %s" % path, "DEBUG")
    
    # HTTP/1.0 didn't have Range/Accept-Ranges headers, or the 206 code
    if cherrypy.response.version >= "1.1":
        response.headers["Accept-Ranges"] = "bytes"
        r = httptools.getRanges(cherrypy.request.headers.get('Range'), c_len)
        if r == []:
            response.headers['Content-Range'] = "bytes */%s" % c_len
            message = "Invalid Range (first-byte-pos greater than Content-Length)"
            raise cherrypy.HTTPError(416, message)
        if r:
            if len(r) == 1:
                # Return a single-part response.
                start, stop = r[0]
                r_len = stop - start
                response.status = "206 Partial Content"
                response.headers['Content-Range'] = ("bytes %s-%s/%s" %
                                                       (start, stop - 1, c_len))
                response.headers['Content-Length'] = r_len
                bodyfile.seek(start)
                response.body = bodyfile.read(r_len)
            else:
                # Return a multipart/byteranges response.
                response.status = "206 Partial Content"
                boundary = mimetools.choose_boundary()
                ct = "multipart/byteranges; boundary=%s" % boundary
                response.headers['Content-Type'] = ct
##                del response.headers['Content-Length']
                
                def fileRanges():
                    # Apache compatibility:
                    yield "\r\n"
                    
                    for start, stop in r:
                        yield "--" + boundary
                        yield "\r\nContent-type: %s" % contentType
                        yield ("\r\nContent-range: bytes %s-%s/%s\r\n\r\n"
                               % (start, stop - 1, c_len))
                        bodyfile.seek(start)
                        yield bodyfile.read(stop - start)
                        yield "\r\n"
                    # Final boundary
                    yield "--" + boundary + "--"
                    
                    # Apache compatibility:
                    yield "\r\n"
                response.body = fileRanges()
        else:
            response.headers['Content-Length'] = c_len
            response.body = bodyfile
    else:
        response.headers['Content-Length'] = c_len
        response.body = bodyfile
    return response.body
serve_file = serveFile

def serve_download(path, name=None):
    """Serve 'path' as an application/x-download attachment."""
    # This is such a common idiom I felt it deserved its own wrapper.
    return serve_file(path, "application/x-download", "attachment", name)

def fileGenerator(input, chunkSize=65536):
    """Yield the given input (a file object) in chunks (default 64k)."""
    chunk = input.read(chunkSize)
    while chunk:
        yield chunk
        chunk = input.read(chunkSize)
    input.close()

def modules(modulePath):
    """Load a module and retrieve a reference to that module."""
    try:
        mod = sys.modules[modulePath]
        if mod is None:
            raise KeyError()
    except KeyError:
        # The last [''] is important.
        mod = __import__(modulePath, globals(), locals(), [''])
    return mod

def attributes(fullAttributeName):
    """Load a module and retrieve an attribute of that module."""
    
    # Parse out the path, module, and attribute
    lastDot = fullAttributeName.rfind(u".")
    attrName = fullAttributeName[lastDot + 1:]
    modPath = fullAttributeName[:lastDot]
    
    aMod = modules(modPath)
    # Let an AttributeError propagate outward.
    try:
        attr = getattr(aMod, attrName)
    except AttributeError:
        raise AttributeError("'%s' object has no attribute '%s'"
                             % (modPath, attrName))
    
    # Return a reference to the attribute.
    return attr


class WSGIApp(object):
    """a convenience class that uses the WSGIAppFilter
    
    to easily add a WSGI application to the CP object tree.

    example:
    cherrypy.tree.mount(SomeRoot(), '/')
    cherrypy.tree.mount(WSGIApp(other_wsgi_app), '/ext_app')
    """
    def __init__(self, app, env_update=None):
        self._cpFilterList = [WSGIAppFilter(app, env_update)]


# public domain "unrepr" implementation, found on the web and then improved.

def getObj(s):
    try:
        import compiler
    except ImportError:
        # Fallback to eval when compiler package is not available,
        # e.g. IronPython 1.0.
        return eval(s)
    
    s = "a=" + s
    p = compiler.parse(s)
    return p.getChildren()[1].getChildren()[0].getChildren()[1]


class UnknownType(Exception):
    pass


class Builder:
    
    def build(self, o):
        m = getattr(self, 'build_' + o.__class__.__name__, None)
        if m is None:
            raise UnknownType(o.__class__.__name__)
        return m(o)
    
    def build_CallFunc(self, o):
        callee, args, starargs, kwargs = map(self.build, o.getChildren())
        return callee(args, *(starargs or ()), **(kwargs or {}))
    
    def build_List(self, o):
        return map(self.build, o.getChildren())
    
    def build_Const(self, o):
        return o.value
    
    def build_Dict(self, o):
        d = {}
        i = iter(map(self.build, o.getChildren()))
        for el in i:
            d[el] = i.next()
        return d
    
    def build_Tuple(self, o):
        return tuple(self.build_List(o))
    
    def build_Name(self, o):
        if o.name == 'None':
            return None
        if o.name == 'True':
            return True
        if o.name == 'False':
            return False
        
        # See if the Name is a package or module
        try:
            return modules(o.name)
        except ImportError:
            pass
        
        raise UnknownType(o.name)
    
    def build_Add(self, o):
        real, imag = map(self.build_Const, o.getChildren())
        try:
            real = float(real)
        except TypeError:
            raise UnknownType('Add')
        if not isinstance(imag, complex) or imag.real != 0.0:
            raise UnknownType('Add')
        return real+imag
    
    def build_Getattr(self, o):
        parent = self.build(o.expr)
        return getattr(parent, o.attrname)
    
    def build_NoneType(self, o):
        return None
    
    def build_UnarySub(self, o):
        return -self.build_Const(o.getChildren()[0])
    
    def build_UnaryAdd(self, o):
        return self.build_Const(o.getChildren()[0])


def unrepr(s):
    if not s:
        return s
    return Builder().build(getObj(s))


def referer(pattern, accept=True, accept_missing=False, error=403,
            message='Forbidden Referer header.'):
    """Raise HTTPError if Referer header does not pass our test.
    
    pattern: a regular expression pattern to test against the Referer.
    accept: if True, the Referer must match the pattern; if False,
        the Referer must NOT match the pattern.
    accept_missing: if True, permit requests with no Referer header.
    error: the HTTP error code to return to the client on failure.
    message: a string to include in the response body on failure.
    """
    try:
        match = bool(re.match(pattern, cherrypy.request.headers['Referer']))
        if accept == match:
            return
    except KeyError:
        if accept_missing:
            return
    
    raise cherrypy.HTTPError(error, message)

def accept(media=None):
    """Return the client's preferred media-type (from the given Content-Types).
    
    If 'media' is None (the default), no test will be performed.
    
    If 'media' is provided, it should be the Content-Type value (as a string)
    or values (as a list or tuple of strings) which the current request
    can emit. The client's acceptable media ranges (as declared in the
    Accept request header) will be matched in order to these Content-Type
    values; the first such string is returned. That is, the return value
    will always be one of the strings provided in the 'media' arg (or None
    if 'media' is None).
    
    If no match is found, then HTTPError 406 (Not Acceptable) is raised.
    Note that most web browsers send */* as a (low-quality) acceptable
    media range, which should match any Content-Type. In addition, "...if
    no Accept header field is present, then it is assumed that the client
    accepts all media types."
    
    Matching types are checked in order of client preference first,
    and then in the order of the given 'media' values.
    
    Note that this function does not honor accept-params (other than "q").
    """
    if not media:
        return
    if isinstance(media, basestring):
        media = [media]
    
    # Parse the Accept request header, and try to match one
    # of the requested media-ranges (in order of preference).
    ranges = cherrypy.request.headers.elements('Accept')
    if not ranges:
        # Any media type is acceptable.
        return media[0]
    else:
        # Note that 'ranges' is sorted in order of preference
        for element in ranges:
            if element.qvalue > 0:
                if element.value == "*/*":
                    # Matches any type or subtype
                    return media[0]
                elif element.value.endswith("/*"):
                    # Matches any subtype
                    mtype = element.value[:-1]  # Keep the slash
                    for m in media:
                        if m.startswith(mtype):
                            return m
                else:
                    # Matches exact value
                    if element.value in media:
                        return element.value
    
    # No suitable media-range found.
    ah = cherrypy.request.headers.get('Accept')
    if ah is None:
        msg = "Your client did not send an Accept header."
    else:
        msg = "Your client sent this Accept header: %s." % ah
    msg += (" But this resource only emits these media types: %s." %
            ", ".join(media))
    raise cherrypy.HTTPError(406, msg)

