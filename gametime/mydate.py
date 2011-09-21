#!/usr/bin/python

from datetime import datetime
import re

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

"""
Container class for date that can process and compare
dates that contain unknown values, such as:
Q1 2012
TBA 2011
Oct 2011
January 2012
3/13/11
"""
class MyDate:
    def __init__(self, date_str):
        self.year = None
        self.quarter = None
        self.month = None
        self.day = None
        self.initialize(date_str)
        
    def initialize(self, date_str):
        if not date_str:
            return
            
        dt = MyDate.__try_convert_date__(date_str, "%B %d, %Y")
        if dt:
            return self.initialize_from_datetime(dt)
            
        dt = MyDate.__try_convert_date__(date_str, "%b %d, %Y")
        if dt:
            return self.initialize_from_datetime(dt)
          
        dt = MyDate.__try_convert_date__(date_str, "%m/%d/%Y")
        if dt:
            return self.initialize_from_datetime(dt)
        
        dt = MyDate.__try_convert_date__(date_str, "%m/%d/%Y")
        if dt:
            return self.initialize_from_datetime(dt)
            
        dt = MyDate.__try_convert_date__(date_str, "%Y-%m-%d")
        if dt:
            return self.initialize_from_datetime(dt)

        year_match = re.search("(?P<year>(19|20)[0-9][0-9])", date_str)
        if year_match:
            self.year = int(year_match.group("year"))
            date_str = date_str.replace(year_match.group("year"), "").strip()
        
        quarter_match = re.search("Q(?P<quarter>[1-4])", date_str)
        if quarter_match:
            self.quarter = int(quarter_match.group("quarter"))
            date_str = date_str.replace("Q" + quarter_match.group("quarter"), "").strip()
        
        try:
            dt = datetime.strptime(date_str, "%B")
            self.month = dt.month
            self.quarter = MyDate.__month_to_quarter__(self.month)
        except ValueError:
            try:
                dt = datetime.strptime(date_str, "%b")
                self.month = dt.month
                self.quarter = MyDate.__month_to_quarter__(self.month)
            except ValueError:
                pass

    def initialize_from_datetime(self, dt):
        self.year = dt.year
        self.month = dt.month
        self.quarter = MyDate.__month_to_quarter__(self.month)
        self.day = dt.day        

    @staticmethod
    def __try_convert_date__(date_str, format):
        try:
            dt = datetime.strptime(date_str, format)
            return dt
        except ValueError:
            return None
                        
    @staticmethod
    def __month_to_quarter__(month):
        return ((month - 1) / 3) + 1
    
    """
    Compares MyDate values for completeness.
    Result is related to the mydate that is the most precise
    """
    @staticmethod
    def compare_completeness(date1, date2):
        y = MyDate.__compare_values_completeness__(date1.year, date2.year)
        if y != 0:
            return y
        q = MyDate.__compare_values_completeness__(date1.quarter, date2.quarter)
        if q != 0:
            return q
        m = MyDate.__compare_values_completeness__(date1.month, date2.month)
        if m != 0:
            return m
        d = MyDate.__compare_values_completeness__(date1.day, date2.day)
        if d != 0:
            return d
        return 0 # EQUAL        
    
    @staticmethod
    def __compare_values_completeness__(v1, v2):
        if v1 is None and v2 is not None:
            return 1
        elif v2 is None and v1 is not None:
            return -1
        else:
            return 0
    
    @staticmethod
    def __compare_values__(v1, v2):
        if v1 is None and v2 is None:
            return 0
        elif v1 is None:
            return 1
        elif v2 is None:
            return -1
        elif v1 == v2:
            return 0
        else:
            return v1 - v2
            
    """
    Returns:
        < 0 : if self is before other
        = 0 : if self is equal to other
        > 0 : if self is after other
    Note: None is always considered after any actual values
    """    
    @staticmethod
    def compare_dates(date1, date2):
        y = MyDate.__compare_values__(date1.year, date2.year)
        if y != 0:
            return y
        q = MyDate.__compare_values__(date1.quarter, date2.quarter)
        if q != 0:
            return q
        m = MyDate.__compare_values__(date1.month, date2.month)
        if m != 0:
            return m
        d = MyDate.__compare_values__(date1.day, date2.day)
        if d != 0:
            return d
        return 0 # EQUAL
        
    def __cmp__(self, other):
        return MyDate.compare_dates(self, other)
    
    def __str__(self):
        if self.day:
            return "%s %i, %i" % (MONTHS[self.month-1], self.day, self.year)
        elif self.month:
            return "%s %i" % (MONTHS[self.month-1], self.year)
        elif self.quarter:
            return "Q%i %i" % (self.quarter, self.year)
        elif self.year:
            return "TBA %i" % self.year
        else:
            return "TBA"
    
    def __repr__(self):
        return "<MyDate: Y:%s, Q:%s, M:%s, D:%s>" % (self.year, self.quarter, self.month, self.day)
            