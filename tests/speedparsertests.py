#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" """

import time
import difflib
from glob import glob
from unittest import TestCase
import lxml

try:
    from speedparser import speedparser
except ImportError:
    import speedparser

try:
    import simplejson as json
except:
    import json

try:
    from jinja2.filters import do_filesizeformat as sizeformat
except:
    sizeformat = lambda x: "%0.2f b" % x

class TimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, time.struct_time):
            return time.mktime(o)
        if isinstance(o, Exception):
            return repr(o)
        return json.JSONEncoder.default(self, o)

munge_author = speedparser.munge_author




class TestCaseBase(TestCase):
    def assertPrettyClose(self, s1, s2):
        """Assert that two strings are pretty damn near equal.  This gets around
        differences in little tidy nonsense FP does that SP won't do."""
        threshold = 0.10
        if len(s1) > 1024 and len(s2) > 1024:
            threshold = 0.25
        # sometimes the title is just made up of some unicode escapes, and since
        # fp and sp treat these differently, we don't pay attention to differences
        # so long as the length is short
        if '&#' in s1 and '&#' not in s2 and len(s1) < 50:
            return True
        if len(s1.strip()) == 0 and len(s2.strip()) < 25:
            return True
        matcher = difflib.SequenceMatcher(None, s1, s2)
        ratio = matcher.quick_ratio()
        if ratio < threshold:
            longest_block = matcher.find_longest_match(0, len(s1), 0, len(s2))
            if len(s1) and longest_block.size / float(len(s1)) > threshold:
                return
            if longest_block.size < 50:
                raise AssertionError("%s\n ---- \n%s\n are not similar enough (%0.3f < %0.3f, %d)" %\
                        (s1, s2, ratio, threshold, longest_block.size))

    def assertSameEmail(self, em1, em2):
        """Assert two emails are pretty similar.  FP and SP munge emails into
        one format, but SP is more consistent in providing that format than FP
        is."""
        if em1 == em2: return True
        if em1 == munge_author(em2):
            return True
        if em2 == munge_author(em1):
            return True
        if munge_author(em1) == munge_author(em2):
            return True
        # if we just have somehow recorded more information because we are
        # awesome, do not register that as a bug
        if em1 in em2:
            return True
        if '@' not in em1 and '@' not in em2:
            # i've encountered some issues here where both author fields are
            # absolute garbage and feedparser seems to prefer one to the other
            # based on no particular algorithm
            return True
        raise AssertionError("em1 and em2 not similar enough %s != %s" % (em1, em2))

    def assertSameLinks(self, l1, l2):
        l1 = l1.strip('#').lower().strip()
        l2 = l2.strip('#').lower().strip()
        if l1 == l2: return True
        if l1 in l2: return True
        # google uses weird object enclosure stuff that would be slow to
        # parse correctly;  the default link for the entry is good enough
        # in thee cases
        if 'buzz' in l2: return True
        if 'plus.google.com' in l2: return True
        # feedparser actually has a bug here where it'l strip ;'s from &gt; in
        # url, though a javascript: href is probably utter garbage anyway
        if l2.startswith('javascript:'):
            return self.assertPrettyClose(l1, l2)
        raise AssertionError('link1 and link2 are not similar enough %s != %s' % (l1, l2))

    def assertSameTime(self, t1, t2):
        if not t1 and not t2: return True
        if t1 == t2: return True
        gt1 = time.gmtime(time.mktime(t1))
        gt2 = time.gmtime(time.mktime(t2))
        if t1 == gt2: return True
        if t2 == gt1: return True
        raise AssertionError("time1 and time2 are not similar enough (%r != %r)" % (t1, t2))


class SpeedTest(TestCaseBase):
    def setUp(self):
        self.files = [f for f in glob('feeds/*.dat') if not f.startswith('.')]
        self.files.sort()

    def test_speed(self):
        total = len(self.files)
        total = 300
        def getspeed(parser, files):
            fullsize = 0
            t0 = time.time()
            for f in files:
               
                with open(f, "rb") as fo:
                    document = fo.read()
                    fullsize += len(document)
                    print ("Open %s"%f)
                    try:
                        elem = parser.parse(document)
                    except speedparser.IncompatibleFeedError as e:
                        print(e)
                    except lxml.etree.XMLSyntaxError as e:
                        print(e)
                    except lxml.etree.ParserError as e:
                        print(e)
                    print(len(elem.entries))
            td = time.time() - t0
            return td, fullsize
        #fpspeed = getspeed(feedparser, self.files[:total])
        spspeed, fullsize = getspeed(speedparser, self.files[:total])
        pct = lambda x: total/x
        print("speedparser: %0.2f/sec, %s/sec" % (pct(spspeed), sizeformat(fullsize/spspeed)))
        #print "feedparser: %0.2f/sec,  speedparser: %0.2f/sec" % (pct(fpspeed), pct(spspeed))

class SpeedTestNoClean(TestCaseBase):
    def setUp(self):
        self.files = [f for f in glob('feeds/*.dat') if not f.startswith('.')]
        self.files.sort()

    def test_speed(self):
        total = len(self.files)
        def getspeed(parser, files, args=[]):
            fullsize = 0
            t0 = time.time()
            for f in files:
                with open(f, "rb") as fo:
                    document = fo.read()
                    fullsize += len(document)
                try:
                    parser.parse(document, *args)
                except:
                    pass
            td = time.time() - t0
            return td, fullsize
        #fpspeed = getspeed(feedparser, self.files[:total])
        spspeed, fullsize = getspeed(speedparser, self.files[:total], args=(False,))
        pct = lambda x: total/x
        print("speedparser (no html cleaning): %0.2f/sec, %s/sec" % (pct(spspeed), sizeformat(fullsize/spspeed)))
        #print "feedparser: %0.2f/sec,  speedparser: %0.2f/sec (html cleaning disabled)" % (pct(fpspeed), pct(spspeed))




