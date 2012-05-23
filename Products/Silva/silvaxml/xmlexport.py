# Copyright (c) 2003-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

from zope.component import getUtility
from zope.interface import Interface
from zope.traversing.browser import absoluteURL
from five import grok

from Acquisition import aq_base
from DateTime import DateTime

from Products.SilvaMetadata.interfaces import IMetadataService
from silva.core import interfaces
from silva.core.interfaces import IExportSettings
from silva.core.interfaces import ISilvaXMLExportHandler, IXMLZEXPExportable
from silva.core.interfaces import IPublicationWorkflow
from silva.core.interfaces.errors import ExternalReferenceError
from silva.core.references.interfaces import IReferenceService
from silva.core.references.utils import canonical_path, relative_path
from silva.translations import translate as _
from sprout.saxext import xmlexport

from Products.Silva.ExtensionRegistry import extensionRegistry
from Products.Silva.ExtensionRegistry import meta_types_for_interface
from Products.Silva.silvaxml import NS_SILVA_URI
from Products.Silva.silvaxml import NS_SILVA_CONTENT_URI, NS_SILVA_EXTRA_URI


class SilvaProducer(xmlexport.Producer):
    grok.baseclass()
    grok.implements(ISilvaXMLExportHandler)

    def relative_path_to(self, content):
        origin_path = self.getInfo().root.getRoot().getPhysicalPath()
        dest_path = content.getPhysicalPath()
        rel_path = "/".join(relative_path(origin_path, dest_path))
        return canonical_path(rel_path)

    def reference(self, name):
        """Return a path to refer an object in the export of a
        reference tagged name.
        """
        service = getUtility(IReferenceService)
        reference = service.get_reference(self.context, name=name)
        if reference is None:
            return None
        info = self.getInfo()
        root = info.root
        if not self.getSettings().externalRendering():
            if not reference.target_id:
                # The reference is broken. Return an empty path.
                return ""
            if not reference.is_target_inside_container(root):
                raise ExternalReferenceError(
                    _(u"External references"),
                    self.context, reference.target, root)
            # Add root path id as it is always mentioned in exports
            return canonical_path('/'.join(
                    [root.getId()] + reference.relative_path_to(root)))
        else:
            # Return url to the target
            return absoluteURL(reference.target, info.request)

    def metadata(self):
        """Export the metadata
        """
        binding = getUtility(IMetadataService).getMetadata(self.context)
        if binding is None:
            return
        # Don't acquire metadata only for the root of the xmlexport
        acquire_metadata = int(self.getInfo().root is self.context)

        self.startElement('metadata')
        set_ids = binding.collection.keys()
        set_ids.sort()

        for set_id in set_ids:
            set_obj = binding.collection[set_id]
            prefix, namespace = set_obj.getNamespace()
            if (namespace != NS_SILVA_CONTENT_URI and
                namespace != NS_SILVA_EXTRA_URI):
                self.handler.startPrefixMapping(prefix, namespace)
            self.startElement('set', {'id': set_id})
            items = binding._getData(set_id, acquire=acquire_metadata).items()
            items.sort()
            for key, value in items:
                if not hasattr(aq_base(set_obj), key):
                    continue
                field = binding.getElement(set_id, key).field
                self.startElementNS(namespace, key)
                if value is not None:
                    field.validator.serializeValue(field, value, self)
                self.endElementNS(namespace, key)
            self.endElement('set')
        self.endElement('metadata')

# Constant to select which version you want for versioned content. Can
# be set on settings.

ALL_VERSION = object()
PREVIEWABLE_VERSION = object()
EDITABLE_VERSION = object()
VIEWABLE_VERSION = object()


class SilvaVersionedContentProducer(SilvaProducer):
    """Base Class for all versioned content
    """
    grok.baseclass()

    def workflow(self):
        """Export the XML for the versioning workflow
        """
        if not self.getSettings().workflow:
            return
        self.startElement('workflow')
        version = self.context.get_unapproved_version_data()
        if version[0]:
            self.workflow_version(version, 'unapproved')
        version = self.context.get_approved_version_data()
        if version[0]:
            self.workflow_version(version, 'approved')
        version = self.context.get_public_version_data()
        if version[0]:
            self.workflow_version(version, 'public')
        for version in self.context.get_previous_versions_data():
            self.workflow_version(version, 'closed')
        self.endElement('workflow')

    def workflow_version(self, version, status):
        """Export the XML for the different workflow versions. (Right now:
        Published, Approved, Unapproved, and Closed, but to the XML these
        are arbitrary)
        """
        id, publication_datetime, expiration_datetime = version
        self.startElement('version', {'id':id})
        self.startElement('status')
        self.handler.characters(status)
        self.endElement('status')
        self.startElement('publication_datetime')
        if publication_datetime:
            if type(publication_datetime) == type(DateTime()):
                self.handler.characters(str(publication_datetime.HTML4()))
            else:
                self.handler.characters(unicode(str(publication_datetime)))
        self.endElement('publication_datetime')
        self.startElement('expiration_datetime')
        if expiration_datetime:
            if type(expiration_datetime) == type(DateTime()):
                self.handler.characters(str(expiration_datetime.HTML4()))
            else:
                self.handler.characters(unicode(str(expiration_datetime)))
        self.endElement('expiration_datetime')
        self.endElement('version')

    def versions(self):
        """Export the XML of the versions themselves.
        """
        wanted = self.getSettings().version
        if wanted is ALL_VERSION:
            for version in IPublicationWorkflow(self.context).get_versions():
                # getVersions will order by id - most recent last.
                self.subsax(version)
        else:
            if wanted is PREVIEWABLE_VERSION:
                version = self.context.get_previewable()
            elif wanted is EDITABLE_VERSION:
                version = self.context.get_editable()
            elif wanted is VIEWABLE_VERSION:
                version = self.context.get_viewable()
            if version:
                self.subsax(version)

    def metadata(self):
        """Versioned Content has no metadata, the metadata is all on the
        versions themselves.
        """
        return


class SilvaContainerProducer(SilvaProducer):
    """Base to export a Silva container to XML.
    """
    grok.baseclass()

    def contents(self):
        settings = self.getSettings()
        self.startElement('content')
        default = self.context.get_default()
        if default is not None:
            self.startElement('default')
            self.subsax(default)
            self.endElement('default')
        for content in self.context.get_ordered_publishables():
            if (interfaces.IPublication.providedBy(content) and
                not settings.withSubPublications()):
                continue
            self.subsax(content)
        for content in self.context.get_non_publishables():
            self.subsax(content)
        if settings.otherContent():
            meta_types = meta_types_for_interface(IXMLZEXPExportable)
            for content in self.context.objectValues(meta_types):
                self.subsax(content)
        self.endElement('content')


class FolderProducer(SilvaContainerProducer):
    """Export a Silva Folder object to XML.
    """
    grok.adapts(interfaces.IFolder, Interface)

    def sax(self):
        self.startElement('folder', {'id': self.context.id})
        self.metadata()
        self.contents()
        self.endElement('folder')


class PublicationProducer(SilvaContainerProducer):
    """Export a Silva Publication object to XML.
    """
    grok.adapts(interfaces.IPublication, Interface)

    def sax(self):
        self.startElement('publication', {'id': self.context.id})
        self.metadata()
        self.contents()
        self.endElement('publication')


class LinkProducer(SilvaVersionedContentProducer):
    """Export a Silva Link object to XML.
    """
    grok.adapts(interfaces.ILink, Interface)

    def sax(self):
        self.startElement('link', {'id': self.context.id})
        self.workflow()
        self.versions()
        self.endElement('link')


class LinkVersionProducer(SilvaProducer):
    """Export a version of a Silva Link object to XML.
    """
    grok.adapts(interfaces.ILinkVersion, Interface)

    def sax(self):
        self.startElement('content', {'version_id': self.context.id})
        self.metadata()
        if self.context.get_relative():
            tag = 'target'
            if self.getSettings().externalRendering():
                tag = 'url'
            self.startElement(tag)
            self.handler.characters(self.reference(u'link'))
            self.endElement(tag)
        else:
            self.startElement('url')
            self.handler.characters(self.context.get_url())
            self.endElement('url')
        self.endElement('content')


class GhostProducer(SilvaVersionedContentProducer):
    """Export a Silva Ghost object to XML.
    """
    grok.adapts(interfaces.IGhost, Interface)

    def sax(self):
        self.startElement('ghost', {'id': self.context.id})
        self.workflow()
        self.versions()
        self.endElement('ghost')


class GhostVersionProducer(SilvaProducer):
    """Export a verson of a Silva Ghost object to XML.
    This actually exports the object the ghost refers to, with the ghost id and
    reference added as attributes.
    """
    grok.adapts(interfaces.IGhostVersion, Interface)

    def sax(self):
        self.startElement('content', {'version_id': self.context.id})
        self.startElement('haunted')
        self.handler.characters(self.reference(u'haunted'))
        self.endElement('haunted')
        if self.getSettings().externalRendering():
            # Include an export of the haunted object, for external
            # rendering.
            haunted = self.context.get_haunted()
            if haunted is not None:
                content = haunted.get_viewable()
                if content is not None:
                    self.subsax(content)
        self.endElement('content')


class GhostFolderProducer(SilvaProducer):
    """Export a Silva Ghost Folder object to XML.
    """
    grok.adapts(interfaces.IGhostFolder, Interface)

    def sax(self):
        self.startElement('ghost_folder', {'id': self.context.id})
        self.startElement('content')
        self.startElement('haunted')
        self.handler.characters(self.reference(u'haunted'))
        self.endElement('haunted')
        self.endElement('content')
        self.endElement('ghost_folder')


class AutoTOCProducer(SilvaProducer):
    """Export an AutoTOC object to XML.
    """
    grok.adapts(interfaces.IAutoTOC, Interface)

    def sax(self):
        self.startElement(
            'auto_toc',
            {'id': self.context.id,
             'depth': str(self.context.get_toc_depth()),
             'types': ','.join(self.context.get_local_types()),
             'sort_order': self.context.get_sort_order(),
             'show_icon': str(self.context.get_show_icon()),
             'display_desc_flag': str(self.context.get_display_desc_flag())})
        self.metadata()
        self.endElement('auto_toc')


class FileProducer(SilvaProducer):
    """Export a File object to XML.
    """
    grok.adapts(interfaces.IFile, Interface)

    def sax(self):
        path = self.context.getPhysicalPath()
        info = self.getInfo()
        self.startElement('file', {'id': self.context.id})
        self.metadata()
        info.addAssetPath(path)
        self.startElement('asset', {'id': info.getAssetPathId(path)})
        self.endElement('asset')
        self.endElement('file')


class ImageProducer(SilvaProducer):
    """Export an Image object to XML.
    """
    grok.adapts(interfaces.IImage, Interface)

    def sax(self):
        path = self.context.getPhysicalPath()
        info = self.getInfo()
        self.startElement('image', {
            'id': self.context.id,
            'web_format': self.context.get_web_format(),
            'web_scale': self.context.get_web_scale(),
            'web_crop': self.context.get_web_crop(),
            })
        self.metadata()
        info.addAssetPath(path)
        self.startElement('asset', {'id': info.getAssetPathId(path)})
        self.endElement('asset')
        self.endElement('image')


class IndexerProducer(SilvaProducer):
    """Export an IndexerProducer to XML.
    """
    grok.adapts(interfaces.IIndexer, Interface)

    def sax(self):
        self.startElement('indexer', {'id': self.context.id})
        self.metadata()
        self.endElement('indexer')


class ZexpProducer(SilvaProducer):
    """Export any unknown content type to a zexp in the zip-file.
    """
    grok.baseclass()

    def sax(self):
        info = self.getInfo()
        if info is not None:
            path = self.context.getPhysicalPath()
            id = self.context.id
            if callable(id):
                id = id()
            meta_type = getattr(aq_base(self.context), 'meta_type', '')
            self.startElement(
                'unknown_content', {'id': id, 'meta_type': meta_type})
            info.addZexpPath(path)
            self.startElement('zexp', {'id': info.getZexpPathId(path)})
            self.endElement('zexp')
            self.endElement('unknown_content')


class SilvaExportRoot(object):

    def __init__(self, exportable):
        self.__exportable = exportable

    def getSilvaVersion(self):
        return 'Silva %s' % extensionRegistry.get_extension('Silva').version

    def getExportable(self):
        return self.__exportable


class SilvaExportRootProducer(xmlexport.BaseProducer):

    def sax(self):
        self.startElement(
            'silva',
            {'silva_version': self.context.getSilvaVersion()})
        self.subsax(self.context.getExportable())
        self.endElement('silva')


class ExportSettings(xmlexport.BaseSettings):
    grok.implements(IExportSettings)

    def __init__(self, asDocument=True, outputEncoding='utf-8',
                 workflow=True, allVersions=True,
                 withSubPublications=True, otherContent=True, options={}):
        xmlexport.BaseSettings.__init__(self, asDocument, outputEncoding)
        self._workflow = workflow
        self._version = allVersions and ALL_VERSION or PREVIEWABLE_VERSION
        self._with_sub_publications = withSubPublications
        self._render_external = False
        self._other_content = otherContent
        self.options = options

    def setWithSubPublications(self, with_sub_publications):
        self._with_sub_publications = with_sub_publications

    def setLastVersion(self, last_version):
        self._version = last_version and PREVIEWABLE_VERSION or ALL_VERSION

    def setVersion(self, version):
        assert version in [ALL_VERSION, PREVIEWABLE_VERSION,
                           EDITABLE_VERSION, VIEWABLE_VERSION]
        self._version = version

    def setExternalRendering(self, external_rendering):
        self._render_external = external_rendering

    @property
    def workflow(self):
        return self._workflow

    @property
    def version(self):
        return self._version

    def withSubPublications(self):
        return self._with_sub_publications

    def otherContent(self):
        return self._other_content

    def externalRendering(self):
        return self._render_external


class ExportContext(object):

    def __init__(self, root, request=None):
        self.__root = root
        self.__request = request
        self._asset_paths = {}
        self._zexp_paths = {}
        self._last_asset_id = 0
        self._last_zexp_id = 0

    @property
    def root(self):
        return self.__root

    @property
    def request(self):
        return self.__request

    def addAssetPath(self, path):
        self._asset_paths[path] = self._makeUniqueAssetId(path)

    def getAssetPathId(self, path):
        return self._asset_paths[path]

    def getAssetPaths(self):
        return self._asset_paths.items()

    def _makeUniqueAssetId(self, path):
        ext = ''
        name = path[-1]
        if len(name) > 4:
            if name[-4] == '.':
                ext = name[-4:]
        self._last_asset_id += 1
        return str(self._last_asset_id) + ext

    def addZexpPath(self, path):
        self._zexp_paths[path] = self._makeUniqueZexpId(path)

    def getZexpPathId(self, path):
        return self._zexp_paths[path]

    def getZexpPaths(self):
        return self._zexp_paths.items()

    def _makeUniqueZexpId(self, path):
        self._last_zexp_id += 1
        return str(self._last_zexp_id) + '.zexp'


# Create and configuration the xml exporter

theXMLExporter = xmlexport.Exporter(NS_SILVA_URI)
theXMLExporter.registerNamespace('silva-content', NS_SILVA_CONTENT_URI)
theXMLExporter.registerNamespace('silva-extra', NS_SILVA_EXTRA_URI)
theXMLExporter.registerProducer(SilvaExportRoot, SilvaExportRootProducer)
theXMLExporter.registerFallbackProducer(ZexpProducer)

# Shortcuts
registerNamespace = theXMLExporter.registerNamespace


def exportToString(context, request=None, settings=None):
    """Export a Silva Object to a XML string.
    """
    if settings is None:
        settings = ExportSettings()
    info = ExportContext(context, request=request)

    return theXMLExporter.exportToString(
        SilvaExportRoot(context),
        settings,
        info), info


# BBB
SilvaBaseProducer = SilvaProducer
VersionedContentProducer = SilvaVersionedContentProducer
