#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2011 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# XSPF playlist parser module for gPodder
# Thomas Perl <thp@gpodder.org>; 2010-08-07


# Currently, this is restricted to FM4 On Demand content, as the XSPF parser
# here isn't generic enough to parse all other feeds reliably. Please get in
# touch if you want support for other feeds - you can use the existing parser
# as a template for your own! :)
#
# See http://fm4.orf.at/radio/stories/audio for available feeds


import os
import time

import re
import feedparser

from xml.dom import minidom

from feedservice.urlstore import get_url
from feedservice.parserservice.models import Feed, Episode
from feedservice.parserservice.mimetype import get_mimetype


class FM4OnDemandPlaylist(Feed):

    URL_REGEX = re.compile('http://onapp1\.orf\.at/webcam/fm4/fod/([^/]+)\.xspf$')

    CONTENT = {
            'spezialmusik': (
                'FM4 Sendungen',
                'http://onapp1.orf.at/webcam/fm4/fod/SOD_Bild_Spezialmusik.jpg',
                'http://fm4.orf.at/',
                'Sendungen jeweils sieben Tage zum Nachhören.',
            ),
            'unlimited': (
                'FM4 Unlimited',
                'http://onapp1.orf.at/webcam/fm4/fod/SOD_Bild_Unlimited.jpg',
                'http://fm4.orf.at/unlimited',
                'Montag bis Freitag (14-15 Uhr)',
            ),
            'soundpark': (
                'FM4 Soundpark',
                'http://onapp1.orf.at/webcam/fm4/fod/SOD_Bild_Soundpark.jpg',
                'http://fm4.orf.at/soundpark',
                'Nacht von Sonntag auf Montag (1-6 Uhr)',
            ),
    }


    @classmethod
    def handles_url(cls, url):
        return bool(cls.URL_REGEX.match(url))


    def get_text_contents(self, node):
        if hasattr(node, '__iter__'):
            return u''.join(self.get_text_contents(x) for x in node)
        elif node.nodeType == node.TEXT_NODE:
            return node.data
        else:
            return u''.join(self.get_text_contents(c) for c in node.childNodes)


    def __init__(self, feed_url, content):

        self.category = self.get_category(feed_url)
        # TODO: Use proper caching of contents with support for
        #       conditional GETs (If-Modified-Since, ETag, ...)
        self.data = minidom.parseString(content)
        self.playlist = self.data.getElementsByTagName('playlist')[0]

        super(FM4OnDemandPlaylist, self).__init__(feed_url)


    def get_category(cls, url):
        m = cls.URL_REGEX.match(url)
        if m is not None:
            return m.group(1)


    def get_title(self):
        title = self.playlist.getElementsByTagName('title')[0]
        default = self.get_text_contents(title)
        return self.CONTENT.get(self.category, \
                (default, None, None, None))[0]


    def get_logo_url(self):
        return self.CONTENT.get(self.category, \
                (None, None, None, None))[1]


    def get_link(self):
        return self.CONTENT.get(self.category, \
                (None, None, 'http://fm4.orf.at/', None))[2]


    def get_description(self):
        return self.CONTENT.get(self.category, \
                (None, None, None, 'XSPF playlist'))[3]


    def get_episode_objects(self):
        tracks = []

        for track in self.playlist.getElementsByTagName('track'):
            title = self.get_text_contents(track.getElementsByTagName('title'))
            url = self.get_text_contents(track.getElementsByTagName('location'))
            episode = FM4Episode(url, title)
            tracks.append(episode)

        return tracks


class FM4Episode(Episode):

    def __init__(self, url, title):
        self.entry = self.get_metadata(url, title)
        super(FM4Episode, self).__init__()


    def get_metadata(self, url, title):
        """Get file download metadata

        Returns a (size, type, name) from the given download
        URL. Will use the network connection to determine the
        metadata via the HTTP header fields.
        """

        resp = get_url(url, headers_only=True)
        filesize = resp[6]
        filetype = resp[5]
        filedate = resp[2]

        entry = {
            'id': url,
            'title': title,
            'url': url,
            'length': int(filesize) if filesize else None,
            'mimetype': filetype,
            'pubDate': filedate,
            }
        return entry


    def get_guid(self):
        return self.entry.get('id', None)


    def get_title(self):
        return self.entry.get('title', None)


    def list_files(self):
        url = self.entry.get('url', False)
        if not url:
            return

        mimetype = get_mimetype(self.entry.get('mimetype', None), url)
        filesize = self.entry.get('length', None)
        yield (url, mimetype, filesize)


    def get_timestamp(self):
        try:
            return int(self.entry.get('pubDate', None))
        except:
            return None
