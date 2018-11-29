#!/usr/bin/env python
#
# Copyright 2015 Allister Banks and Tim Sutton,
# based on MSOffice2011UpdateInfoProvider by Greg Neagle
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# Disabling 'no-env-member' for recipe processors
#pylint:disable=e1101
"""See docstring for MSOffice2019VersionProvider class"""

import plistlib
import re
import urllib2

from autopkglib import Processor, ProcessorError


__all__ = ["MSOffice2019VersionProvider"]

# Installers are all supposed to be multilingual.
# Only Locale and Channel (Prod vs. Insider Slow/Fast) options available
BASE_URL = "https://officecdn.microsoft.com/pr/%s/OfficeMac/0409%s2019.xml"
PROD_DICT = {
    'Excel': ['XCEL', '525135'],
    'OneNote': ['ONMC', '820886'],
    'Outlook': ['OPIM', '525137'],
    'PowerPoint': ['PPT3', '525136'],
    'Word': ['MSWD', '525134']
}
CHANNELS = {
    'Production': 'C1297A47-86C4-4C1F-97FA-950631F94777',
    'InsiderSlow': '1AC37578-5A24-40FB-892E-B89D85B6DFAA',
    'InsiderFast': '4B2D7701-0A4F-49C8-B4CB-0C2D4043F51F',
}
DEFAULT_CHANNEL = "Production"


class MSOffice2019VersionProvider(Processor):
    """Provides the version for an individual, standalone MS Office 2019 product."""
    input_variables = {
        "product": {
            "required": True,
            "description": "Name of product to fetch, e.g. Excel.",
        },
        "channel": {
            "required": False,
            "default": DEFAULT_CHANNEL,
            "description":
                ("Update feed channel that will be checked for updates. "
                 "Defaults to %s, acceptable values are one of: %s"
                 % (DEFAULT_CHANNEL,
                    ", ".join(CHANNELS.keys())))
        }
    }
    output_variables = {
        "version": {
            "description":
                ("The installer version as extracted from the Microsoft metadata.")
        },
    }


    def get_version(self, metadata):
        """Extracts the version of the update item."""
        # We currently expect the version at the end of the Title key,
        # e.g.: "Excel Update 16.19.0 (18110915)"
        # Work backwards from the end and break on the first thing
        # that looks like a version
        match = None
        for element in reversed(metadata["Title"].split()):
            match = re.match(r"(\d+\.\d+(\.\d)*)", element)
            if match:
                break
        if not match:
            raise ProcessorError(
                "Error validating Office 2019 version extracted "
                "from Title manifest value: '%s'" % metadata["Title"])
        version = match.group(0)
        return version


    def main(self):
        """Gets info about the installer in a channel from MAU metadata."""
        self.env["URL"] = "https://go.microsoft.com/fwlink/?linkid=%s" % (PROD_DICT[self.env["product"]][1])
        channel_input = self.env.get("channel", DEFAULT_CHANNEL)
        if channel_input not in CHANNELS.keys():
            raise ProcessorError(
                "'channel' input variable must be one of: %s or a custom "
                "uuid" % (", ".join(CHANNELS.keys())))
        base_url = BASE_URL % (CHANNELS[channel_input], PROD_DICT[self.env["product"]][0])
        # Get metadata URL
        req = urllib2.Request(base_url)
        # Add the MAU User-Agent, since MAU feed server seems to explicitly
        # block a User-Agent of 'Python-urllib/2.7' - even a blank User-Agent
        # string passes.
        req.add_header("User-Agent",
                       "Microsoft%20AutoUpdate/3.6.16080300 CFNetwork/760.6.3 Darwin/15.6.0 (x86_64)")

        try:
            fdesc = urllib2.urlopen(req)
            data = fdesc.read()
            fdesc.close()
        except BaseException as err:
            raise ProcessorError("Can't download %s: %s" % (base_url, err))

        metadata = plistlib.readPlistFromString(data)[0]
        self.env["version"] = self.get_version(metadata)


if __name__ == "__main__":
    PROCESSOR = MSOffice2019VersionProvider()
    PROCESSOR.execute_shell()
