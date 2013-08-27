# -*- coding: utf-8 -*-
# Copyright (c) 2003-2013 Infrae. All rights reserved.
# See also LICENSE.txt

from five import grok
from zope.cachedescriptors.property import Lazy
from zope.publisher.interfaces.browser import IBrowserRequest

# Silva
from silva.core import interfaces
from silva.core.views.interfaces import IVirtualSite
from silva.core.interfaces.adapters import IIconResolver


class SilvaIcons(grok.DirectoryResource):
    # This export the globals directory using Zope 3 technology.
    grok.path('icons')
    grok.name('silva.icons')



# GRAVATAR_URL = "https://secure.gravatar.com/avatar.php?"
# GRAVATAR_TEMPLATE = """
# <img src="%(image)s" alt="%(userid)s's avatar" title="%(userid)s's avatar"
#      style="height: %(size)spx; width: %(size)spx" />
# """

# security.declareProtected(SilvaPermissions.AccessContentsInformation,
#                           'avatar_tag')
# def avatar_tag(self, size=32):
#     """HTML <img /> tag for the avatar icon
#     """
#     #See http://en.gravatar.com/site/implement/python
#     email = self.avatar()
#     default = self.get_root_url() + "/globals/avatar.png"

#     if email:
#         url = GRAVATAR_URL + urllib.urlencode(
#             {'gravatar_id':hashlib.md5(email.lower()).hexdigest(),
#              'default':default, 'size':str(size)})
#     else:
#         url = default
#     info = {'userid': self.userid(),
#             'size': size,
#             'image': url}
#     return GRAVATAR_TEMPLATE % info


class IconRegistry(object):
    grok.implements(interfaces.IIconRegistry)

    def __init__(self):
        self._icons = {}

    def get_icon(self, content):
        if interfaces.IGhost.providedBy(content):
            identifier = ('ghost', 'link_ok')
        elif interfaces.IGhostFolder.providedBy(content):
            if content.get_link_status() is None:
                if interfaces.IPublication.providedBy(content.get_haunted()):
                    kind = 'publication'
                else:
                    kind = 'folder'
            else:
                kind = 'link_broken'
            identifier = ('ghostfolder', kind)
        elif interfaces.IFile.providedBy(content):
            identifier = ('mime_type', content.get_mime_type())
        elif interfaces.ISilvaObject.providedBy(content):
            identifier = ('meta_type', content.meta_type)
        else:
            if content is None:
                return '++static++/silva.icons/missing.png'
            if interfaces.IAuthorization.providedBy(content):
                content = content.source
            meta_type = getattr(content, 'meta_type', None)
            if meta_type is None:
                raise ValueError(u"No icon for unknown object %r" % content)
            identifier = ('meta_type', meta_type)
        return self.get_icon_by_identifier(identifier)

    def get_icon_by_identifier(self, identifier):
        icon = self._icons.get(identifier, None)
        if icon is None:
            raise ValueError(u"No icon for %r" % repr(identifier))
        return icon

    def register(self, identifier, icon_name):
        """Register an icon.

        NOTE: this will overwrite previous icon declarations
        """
        assert isinstance(identifier, tuple) and len(identifier) == 2, \
            'Invalid icon identifier'
        self._icons[identifier] = icon_name


@apply
def registry():
    """Create and initialize icon registry with Silva defaults.
    """
    registry = IconRegistry()

    mime_icons = [
        ('application/msword', 'file_doc.png'),
        ('application/pdf', 'file_pdf.png'),
        ('application/postscript', 'file_illustrator.png'),
        ('application/sdp', 'file_quicktime.png'),
        ('application/vnd.ms-excel', 'file_xls.png'),
        ('application/vnd.ms-powerpoint', 'file_ppt.png'),
        ('application/vnd.openxmlformats-officedocument.presentationml.presentation', 'file_ppt.png'),
        ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'file_xls.png'),
        ('application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'file_doc.png'),
        ('application/x-javascript', 'file_js.png'),
        ('application/x-rtsp', 'file_quicktime.png'),
        ('application/x-sdp', 'file_quicktime.png'),
        ('application/x-zip-compressed', 'file_zip.png'),
        ('audio/aiff', 'file_aiff.png'),
        ('audio/basic', 'file_aiff.png'),
        ('audio/mid', 'file_aiff.png'),
        ('audio/midi', 'file_aiff.png'),
        ('audio/mp3', 'file_aiff.png'),
        ('audio/mp4', 'file_aiff.png'),
        ('audio/mpeg', 'file_aiff.png'),
        ('audio/mpeg3', 'file_aiff.png'),
        ('audio/wav', 'file_aiff.png'),
        ('audio/x-aiff', 'file_aiff.png'),
        ('audio/x-gsm', 'file_aiff.png'),
        ('audio/x-m4a', 'file_aiff.png'),
        ('audio/x-m4p', 'file_aiff.png'),
        ('audio/x-midi', 'file_aiff.png'),
        ('audio/x-mp3', 'file_aiff.png'),
        ('audio/x-mpeg', 'file_aiff.png'),
        ('audio/x-mpeg3', 'file_aiff.png'),
        ('audio/x-wav', 'file_aiff.png'),
        ('text/css', 'file_css.png'),
        ('text/html', 'file_html.png'),
        ('text/plain', 'file_txt.png'),
        ('text/xml', 'file_xml.png'),
        ('video/avi', 'file_quicktime.png'),
        ('video/mp4', 'file_quicktime.png'),
        ('video/mpeg', 'file_quicktime.png'),
        ('video/msvideo', 'file_quicktime.png'),
        ('video/quicktime', 'file_quicktime.png'),
        ('video/x-dv', 'file_quicktime.png'),
        ('video/x-mpeg', 'file_quicktime.png'),
        ('video/x-msvideo', 'file_quicktime.png'),
        ]
    for mimetype, icon_name in mime_icons:
        registry.register(
            ('mime_type', mimetype),
            '++static++/silva.icons/%s' % icon_name)

    misc_icons = [
        ('meta_type', None, 'missing.png'),
        ('ghostfolder', 'folder', 'ghost_folder.gif'),
        ('ghostfolder', 'publication', 'ghost_publication.gif'),
        ('ghostfolder', 'link_broken', 'ghost_broken.png'),
        ('ghost', 'link_ok', 'ghost.gif'),
        ('ghost', 'link_broken', 'ghost_broken.png'),
    ]
    for cls, kind, icon_name in misc_icons:
        registry.register(
            (cls, kind),
            '++static++/silva.icons/%s' % icon_name)

    return registry


class IconResolver(grok.Adapter):
    grok.context(IBrowserRequest)
    grok.implements(IIconResolver)

    default = '++static++/silva.icons/generic.gif'

    def __init__(self, request):
        self.request = request

    @Lazy
    def _base_url(self):
        site = IVirtualSite(self.request)
        return site.get_root_url()

    def get_tag(self, content=None, identifier=None):
        if content is not None:
            url = self.get_content_url(content)
            alt = getattr(content, 'meta_type', 'Missing')
        else:
            url = self.get_identifier_url(identifier)
            alt = identifier or 'Missing'
        return """<img height="16" width="16" src="%s" alt="%s" />""" % (
            url, alt)

    def get_identifier(self, identifier):
        try:
            return registry.get_icon_by_identifier(('meta_type', identifier))
        except ValueError:
            return self.default

    def get_content(self, content):
        try:
            return registry.get_icon(content)
        except ValueError:
            return self.default

    def get_content_url(self, content):
        """Return a content icon URL.
        """
        return "/".join((self._base_url, self.get_content(content),))

    def get_identifier_url(self, identifier):
        """Return a URL out of a identifier.
        """
        return "/".join((self._base_url, self.get_identifier(identifier),))
