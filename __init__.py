# Copyright (c) 2002-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import os

# prevent a circular import in Zope 2.12
import AccessControl

# register FileSystemSite directories
from Products.FileSystemSite.DirectoryView import (
    registerDirectory, registerFileExtension)
from Products.FileSystemSite.FSImage import FSImage
from Products import kupu

registerDirectory('%s/common' % os.path.dirname(kupu.__file__), globals())
registerDirectory('%s/kupu' % os.path.dirname(__file__), globals())
registerDirectory('views', globals())
registerDirectory('resources', globals())
registerDirectory('globals', globals())
# enable .ico support for FileSystemSite
registerFileExtension('ico', FSImage)

# register this extension
from silva.core import conf as silvaconf
silvaconf.extensionName('Silva')
silvaconf.extensionTitle('Silva Core')
silvaconf.extensionDepends(None)

#----------------------------------------
# Initialize subscription feature, part 1
#----------------------------------------
try:
    from Products.MaildropHost import MaildropHost
    MAILDROPHOST_AVAILABLE = True
except ImportError:
    MAILDROPHOST_AVAILABLE = False

MAILHOST_ID = 'service_subscriptions_mailhost'


from Products.Silva.Metadata import initialize_metadata
from Products.Silva import mangle # Initialize security ?
# To make the splitter register itself
from Products.Silva import UnicodeSplitter

# Add Formulator fields
from Products.Silva import emaillinesfield, lookupwindowfield, kupupopupfield

# Initialize the XML registries
from Products.Silva.silvaxml import xmlexport
xmlexport.initializeXMLExportRegistry()


def __allow_access_to_unprotected_subobjects__(name, value=None):
    return name in ('mangle', 'batch', 'adapters', 'version_management', 'path')

AccessControl.allow_module('Products.Silva.adapters.views')
AccessControl.allow_module('Products.Silva.adapters.security')
AccessControl.allow_module('Products.Silva.adapters.cleanup')
AccessControl.allow_module('Products.Silva.adapters.renderable')
AccessControl.allow_module('Products.Silva.adapters.version_management')
AccessControl.allow_module('Products.Silva.adapters.archivefileimport')
AccessControl.allow_module('Products.Silva.adapters.languageprovider')
AccessControl.allow_module('Products.Silva.adapters.zipfileimport')
AccessControl.allow_module('Products.Silva.adapters.path')
AccessControl.allow_module('Products.Silva.roleinfo')
AccessControl.allow_module('Products.Silva.i18n')
AccessControl.allow_module('Products.Silva.mail')

def initialize_icons():
    from Products.Silva.icon import registry

    mimeicons = [
        ('audio/aiff', 'file_aiff.png'),
        ('audio/x-aiff', 'file_aiff.png'),
        ('audio/basic', 'file_aiff.png'),
        ('audio/x-gsm', 'file_aiff.png'),
        ('audio/mid', 'file_aiff.png'),
        ('audio/midi', 'file_aiff.png'),
        ('audio/x-midi', 'file_aiff.png'),
        ('audio/mpeg', 'file_aiff.png'),
        ('audio/x-mpeg', 'file_aiff.png'),
        ('audio/mpeg3', 'file_aiff.png'),
        ('audio/x-mpeg3', 'file_aiff.png'),
        ('audio/mp3', 'file_aiff.png'),
        ('audio/x-mp3', 'file_aiff.png'),
        ('audio/x-m4a', 'file_aiff.png'),
        ('audio/x-m4p', 'file_aiff.png'),
        ('audio/mp4', 'file_aiff.png'),
        ('audio/wav', 'file_aiff.png'),
        ('audio/x-wav', 'file_aiff.png'),
        ('application/msword', 'file_doc.png'),
        ('application/postscript', 'file_illustrator.png'),
        ('application/x-javascript', 'file_js.png'),
        ('application/pdf', 'file_pdf.png'),
        ('application/vnd.ms-powerpoint', 'file_ppt.png'),
        ('application/x-rtsp', 'file_quicktime.png'),
        ('application/sdp', 'file_quicktime.png'),
        ('application/x-sdp', 'file_quicktime.png'),
        ('application/vnd.ms-excel', 'file_xls.png'),
        ('application/x-zip-compressed', 'file_zip.png'),
        ('text/plain', 'file_txt.png'),
        ('text/css', 'file_css.png'),
        ('text/html', 'file_html.png'),
        ('text/xml', 'file_xml.png'),
        ('video/avi', 'file_quicktime.png'),
        ('video/msvideo', 'file_quicktime.png'),
        ('video/x-msvideo', 'file_quicktime.png'),
        ('video/mp4', 'file_quicktime.png'),
        ('video/mpeg', 'file_quicktime.png'),
        ('video/x-mpeg', 'file_quicktime.png'),
        ('video/quicktime', 'file_quicktime.png'),
        ('video/x-dv', 'file_quicktime.png'),
    ]
    for mimetype, icon_name in mimeicons:
        registry.registerIcon(
            ('mime_type', mimetype),
            '++resource++silva.icons/%s' % icon_name)

    misc_icons = [
        ('ghostfolder', 'folder', 'silvaghost_folder.gif'),
        ('ghostfolder', 'publication', 'silvaghost_publication.gif'),
        ('ghostfolder', 'link_broken', 'silvaghost_broken.png'),
        ('ghost', 'link_ok', 'silvaghost.gif'),
        ('ghost', 'link_broken', 'silvaghost_broken.png'),
    ]
    for klass, kind, icon_name in misc_icons:
        registry.registerIcon(
            (klass, kind),
            '++resource++silva.icons/%s' % icon_name)


initialize_icons()
initialize_metadata()


#------------------------------------------------------------------------------
# Monkey patches
#------------------------------------------------------------------------------

import monkey
monkey.patch_all()
