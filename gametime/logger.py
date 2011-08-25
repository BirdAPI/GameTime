#!/usr/bin/python

# Based on logger.py from SickBeard (https://github.com/midgetspy/Sick-Beard)

from __future__ import with_statement 

import os
import threading

import logging

import gametime

# number of log files to keep
NUM_LOGS = 3

# log size in bytes
LOG_SIZE = 10000000 # 10 megs

ERROR = logging.ERROR
WARNING = logging.WARNING
MESSAGE = logging.INFO
DEBUG = logging.DEBUG

reverseNames = {u'ERROR': ERROR,
                u'WARNING': WARNING,
                u'INFO': MESSAGE,
                u'DEBUG': DEBUG}

class GTRotatingLogHandler(object):

    def __init__(self, log_file, num_files, num_bytes):
        self.num_files = num_files
        self.num_bytes = num_bytes
        
        self.log_file = log_file
        self.cur_handler = None

        self.writes_since_check = 0

        self.log_lock = threading.Lock()

    def initLogging(self, consoleLogging=True):
    
        self.log_file = os.path.join(gametime.LOG_DIR, self.log_file)
    
        self.cur_handler = self._config_handler()
    
        logging.getLogger('gametime').addHandler(self.cur_handler)
    
        # define a Handler which writes INFO messages or higher to the sys.stderr
        if consoleLogging:
            console = logging.StreamHandler()
    
            console.setLevel(logging.INFO)
    
            # set a format which is simpler for console use
            console.setFormatter(logging.Formatter('%(asctime)s %(levelname)s::%(message)s', '%H:%M:%S'))
    
            # add the handler to the root logger
            logging.getLogger('gametime').addHandler(console)
    
        logging.getLogger('gametime').setLevel(logging.DEBUG)

    def _config_handler(self):
        """
        Configure a file handler to log at file_name and return it.
        """
    
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', '%b-%d %H:%M:%S'))
        return file_handler

    def _log_file_name(self, i):
        """
        Returns a numbered log file name depending on i. If i==0 it just uses logName, if not it appends
        it to the extension (blah.log.3 for i == 3)
        
        i: Log number to ues
        """
        return self.log_file + ('.' + str(i) if i else '')
    
    def _num_logs(self):
        """
        Scans the log folder and figures out how many log files there are already on disk
        
        Returns: The number of the last used file (eg. mylog.log.3 would return 3). If there are no logs it returns -1
        """
        cur_log = 0
        while os.path.isfile(self._log_file_name(cur_log)):
            cur_log += 1
        return cur_log - 1
    
    def _rotate_logs(self):
        
        gt_logger = logging.getLogger('gametime')
        
        # delete the old handler
        if self.cur_handler:
            self.cur_handler.flush()
            self.cur_handler.close()
            gt_logger.removeHandler(self.cur_handler)
    
        # rename or delete all the old log files
        for i in range(self._num_logs(), -1, -1):
            cur_file_name = self._log_file_name(i)
            try:
                if i >= NUM_LOGS:
                    os.remove(cur_file_name)
                else:
                    os.rename(cur_file_name, self._log_file_name(i+1))
            except WindowsError:
                pass
        
        # the new log handler will always be on the un-numbered .log file
        new_file_handler = self._config_handler()
        
        self.cur_handler = new_file_handler
        
        gt_logger.addHandler(new_file_handler)

    def log(self, toLog, logLevel=MESSAGE):
    
        with self.log_lock:
    
            # check the size and see if we need to rotate
            if self.writes_since_check >= 10:
                if os.path.isfile(self.log_file) and os.path.getsize(self.log_file) >= LOG_SIZE:
                    self._rotate_logs()
                self.writes_since_check = 0
            else:
                self.writes_since_check += 1
    
            meThread = threading.currentThread().getName()
            message = meThread + u" :: " + toLog
        
            out_line = message.encode('utf-8')
        
            gt_logger = logging.getLogger('gametime')
    
            try:
                if logLevel == DEBUG:
                    gt_logger.debug(out_line)
                elif logLevel == MESSAGE:
                    gt_logger.info(out_line)
                elif logLevel == WARNING:
                    gt_logger.warning(out_line)
                elif logLevel == ERROR:
                    gt_logger.error(out_line)
                else:
                    gt_logger.log(logLevel, out_line)
            except ValueError:
                pass

gt_log_instance = GTRotatingLogHandler('gametime.log', NUM_LOGS, LOG_SIZE)

def log(toLog, logLevel=MESSAGE):
    gt_log_instance.log(toLog, logLevel)