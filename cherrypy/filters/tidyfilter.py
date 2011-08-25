import cgi
import os
import StringIO
import traceback

import cherrypy
from basefilter import BaseFilter


class TidyFilter(BaseFilter):
    """Filter that runs the response through Tidy.
    
    Note that we use the standalone Tidy tool rather than the python
    mxTidy module. This is because this module doesn't seem to be
    stable and it crashes on some HTML pages (which means that the
    server would also crash)
    """
    
    def before_finalize(self):
        if not cherrypy.config.get('tidy_filter.on', False):
            return
        
        # the tidy filter, by its very nature it's not generator friendly, 
        # so we just collect the body and work with it.
        originalBody = cherrypy.response.collapse_body()
        
        fct = cherrypy.response.headers.get('Content-Type', '')
        ct = fct.split(';')[0]
        encoding = ''
        i = fct.find('charset=')
        if i != -1:
            encoding = fct[i+8:]
        if ct == 'text/html':
            tmpdir = cherrypy.config.get('tidy_filter.tmp_dir')
            pageFile = os.path.join(tmpdir, 'page.html')
            outFile = os.path.join(tmpdir, 'tidy.out')
            errFile = os.path.join(tmpdir, 'tidy.err')
            f = open(pageFile, 'wb')
            f.write(originalBody)
            f.close()
            tidyEncoding = encoding.replace('-', '')
            if tidyEncoding:
                tidyEncoding = '-' + tidyEncoding
            
            strictXml = ""
            if cherrypy.config.get('tidy_filter.strict_xml', False):
                strictXml = ' -xml'
            os.system('"%s" %s%s -f %s -o %s %s' %
                      (cherrypy.config.get('tidy_filter.tidy_path'), tidyEncoding,
                       strictXml, errFile, outFile, pageFile))
            f = open(errFile, 'rb')
            err = f.read()
            f.close()
            
            errList = err.splitlines()
            newErrList = []
            for err in errList:
                if (err.find('Warning') != -1 or err.find('Error') != -1):
                    ignore = 0
                    for errIgn in cherrypy.config.get('tidy_filter.errors_to_ignore', []):
                        if err.find(errIgn) != -1:
                            ignore = 1
                            break
                    if not ignore:
                        newErrList.append(err)
            
            if newErrList:
                newBody = "Wrong HTML:<br />" + cgi.escape('\n'.join(newErrList)).replace('\n','<br />')
                newBody += '<br /><br />'
                i = 0
                for line in originalBody.splitlines():
                    i += 1
                    newBody += "%03d - "%i + cgi.escape(line).replace('\t','    ').replace(' ','&nbsp;') + '<br />'
                
                cherrypy.response.body = newBody
                # Delete Content-Length header so finalize() recalcs it.
                cherrypy.response.headers.pop("Content-Length", None)

            elif strictXml:
                # The HTML is OK, but is it valid XML
                # Use elementtree to parse XML
                from elementtree.ElementTree import parse
                tagList = ['nbsp', 'quot']
                for tag in tagList:
                    originalBody = originalBody.replace(
                        '&' + tag + ';', tag.upper())

                if encoding:
                    originalBody = """<?xml version="1.0" encoding="%s"?>""" % encoding + originalBody
                f = StringIO.StringIO(originalBody)
                try:
                    tree = parse(f)
                except:
                    # Wrong XML
                    bodyFile = StringIO.StringIO()
                    traceback.print_exc(file = bodyFile)
                    cherrypy.response.body = bodyFile.getvalue()
                    # Delete Content-Length header so finalize() recalcs it.
                    cherrypy.response.headers.pop("Content-Length", None)
                    
                    newBody = "Wrong XML:<br />" + cgi.escape(bodyFile.getvalue().replace('\n','<br />'))
                    newBody += '<br /><br />'
                    i = 0
                    for line in originalBody.splitlines():
                        i += 1
                        newBody += "%03d - "%i + cgi.escape(line).replace('\t','    ').replace(' ','&nbsp;') + '<br />'
                    
                    cherrypy.response.body = newBody
                    # Delete Content-Length header so finalize() recalcs it.
                    cherrypy.response.headers.pop("Content-Length", None)

