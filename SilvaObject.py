# Copyright (c) 2002 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id: SilvaObject.py,v 1.90 2003/08/01 15:54:53 faassen Exp $

# python
from types import StringType
# Zope
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from DateTime import DateTime
from StringIO import StringIO
# Silva
import SilvaPermissions
from Products.SilvaViews.ViewRegistry import ViewAttribute
from Security import Security
from ViewCode import ViewCode

from interfaces import ISilvaObject, IContent, IPublishable, IAsset
from interfaces import IContent, IContainer, IPublication
from interfaces import IVersioning, IVersionedContent

class XMLExportContext:
    """Simple context class used in XML export.
    """
    pass

class SilvaObject(Security, ViewCode):
    """Inherited by all Silva objects.
    """
    security = ClassSecurityInfo()

    # FIXME: this is for backward compatibility with old objects
    _title = "No title yet"
    _creation_datetime = None
    _modification_datetime = None
    
    # allow edit view on this object
    edit = ViewAttribute('edit', 'tab_edit')

    # and public as well
    public = ViewAttribute('public', 'render_view')

    # whether the object should be shown in the addables-pulldown
    _is_allowed_in_publication = 1

    # location of the xml schema
    _xml_namespace = "http://www.infrae.com/xml"
    _xml_schema = "silva-0.9.1.xsd"

    def __init__(self, id, title):
        self.id = id
        self._title = title
        self._creation_datetime = self._modification_datetime = DateTime()
        
    def __repr__(self):
        return "<%s instance %s>" % (self.meta_type, self.id)

    # MANIPULATORS
    def manage_afterAdd(self, item, container):
        self._afterAdd_helper(item, container)

    def _afterAdd_helper(self, item, container):
        container._add_ordered_id(item)
        if self.id == 'index':
            container = self.get_container()
            container._invalidate_sidebar(container)
    
    def manage_beforeDelete(self, item, container):
        self._beforeDelete_helper(item, container)

    def _beforeDelete_helper(self, item, container):
        container._remove_ordered_id(item)
        if self.id == 'index':
            container = self.get_container()
            container._invalidate_sidebar(container)

    security.declareProtected(
        SilvaPermissions.ChangeSilvaContent, 'set_title')
    def set_title(self, title):
        """Set the title of the silva object.
        """
        # FIXME: Ugh. I get unicode from formulator but this will not validate
        # when using the metadata system. So first make it into utf-8 again..
        title = title.encode('utf-8')
        binding = self.service_metadata.getMetadata(self)
        binding.setValues(
            'silva-content', {'maintitle': title})
        if self.id == 'index':
            container = self.get_container()
            container._invalidate_sidebar(container)

    security.declarePrivate('titleMutationTrigger')
    def titleMutationTrigger(self):
        """This trigger is called upon save of Silva Metadata. More
        specifically, when the silva-content - defining titles - set is 
        being editted for this object.
        """
        if self.id == 'index':
            container = self.get_container()
            container._invalidate_sidebar(container)

    # ACCESSORS

    security.declareProtected(
        SilvaPermissions.AccessContentsInformation, 'get_silva_object')
    def get_silva_object(self):
        """Get the object. Can be used with acquisition to get the Silva
        Document for a Version object.
        """
        return self.aq_inner

    security.declareProtected(
        SilvaPermissions.AccessContentsInformation, 'silva_object_url')
    def silva_object_url(self):
        """Get url for silva object.
        """
        return self.get_silva_object().absolute_url()

    security.declareProtected(
        SilvaPermissions.AccessContentsInformation, 'get_title')
    def get_title(self):
        """Get the title of the silva object.
        """
        binding = self.service_metadata.getMetadata(self)
        return binding.get(
            'silva-content', element_id='maintitle')

    security.declareProtected(
        SilvaPermissions.AccessContentsInformation, 'get_short_title')
    def get_short_title(self):
        """Get the title of the silva object.
        """
        binding = self.service_metadata.getMetadata(self)
        short_title = binding.get(
            'silva-content', element_id='shorttitle')
        if not short_title:
            return self.get_title()
        return short_title

    security.declareProtected(
        SilvaPermissions.AccessContentsInformation, 'get_title_or_id')
    def get_title_or_id(self):
        """Get title or id if not available.
        """
        title = self.get_title()
        if not title.strip():
            title = self.id
        return title

    security.declareProtected(
        SilvaPermissions.AccessContentsInformation, 'get_title_editable')
    def get_title_editable(self):
        """Get the title of the editable version if possible.
        """
        return self.get_title()

    security.declareProtected(
        SilvaPermissions.AccessContentsInformation, 'get_title_editable')
    def get_short_title_editable(self):
        """Get the short title of the editable version if possible.
        """
        return self.get_short_title()

    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'get_title_or_id_editable')
    def get_title_or_id_editable(self):
        """Get the title of the editable version if possible, or id if
        not available.
        """
        return self.get_title_or_id()

    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'get_creation_datetime')
    def get_creation_datetime(self):
        """Return creation datetime."""
        return self._creation_datetime
    
    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'get_modification_datetime')
    def get_modification_datetime(self, update_status=1):
        """Return modification datetime."""
        version = self.get_previewable()
        assert version is not None
        binding = self.service_metadata.getMetadata(version)
        if binding is None:
            return None
        last_modification = binding.get('silva-extra',
            element_id='modificationtime', no_defaults=1)
        return last_modification

    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'get_breadcrumbs')
    def get_breadcrumbs(self, ignore_index=1):
        """Get information used to display breadcrumbs. This is a
        list of items from the Silva Root.
        """
        result = []
        item = self
        while ISilvaObject.isImplementedBy(item):
            # Should the index be included?
            if ignore_index:
                if not (IContent.isImplementedBy(item) 
                        and item.is_default()):
                    result.append(item)
            else:
                result.append(item)
            item = item.aq_parent
        result.reverse()
        return result
        
    security.declareProtected(SilvaPermissions.ChangeSilvaContent,
                              'get_editable')
    def get_editable(self):
        """Get the editable version (may be object itself if no versioning).
        """
        return self

    security.declareProtected(SilvaPermissions.ReadSilvaContent,
                              'get_previewable')
    def get_previewable(self):
        """Get the previewable version (may be the object itself if no
        versioning).
        """
        return self
    
    security.declareProtected(SilvaPermissions.View, 'get_viewable')
    def get_viewable(self):
        """Get the publically viewable version (may be the object itself if
        no versioning).
        """
        return self

    security.declareProtected(SilvaPermissions.ReadSilvaContent, 'preview')
    def preview(self, view_type='public'):
        """Render this as preview with the public view. If this is no previewable,
        should return something indicating this.
        """
        return self.service_view_registry.render_preview(view_type, self)

    security.declareProtected(SilvaPermissions.View, 'view')
    def view(self, view_type='public'):
        """Render this with the public view. If there is no viewable,
        should return something indicating this.
        """
        return self.service_view_registry.render_view(view_type, self)

    # these help the UI that can't query interfaces directly

    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'implements_publishable')
    def implements_publishable(self):
        return IPublishable.isImplementedBy(self)
    
    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'implements_asset')  
    def implements_asset(self):
        return IAsset.isImplementedBy(self)

    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'implements_content')
    def implements_content(self):
        return IContent.isImplementedBy(self)

    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'implements_container')
    def implements_container(self):
        return IContainer.isImplementedBy(self)

    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'implements_publication')
    def implements_publication(self):
        return IPublication.isImplementedBy(self)
    
    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'implements_versioning')
    def implements_versioning(self):
        return IVersioning.isImplementedBy(self)

    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'implements_versioned_content')
    def implements_versioned_content(self):
        return IVersionedContent.isImplementedBy(self)

    security.declareProtected(
        SilvaPermissions.ViewAuthenticated, 'security_trigger')
    def security_trigger(self):
        """This is equivalent to activate_security_hack(), however this 
        method's name is less, er, hackish... (e.g. when visible in error
        messages and trace-backs).
        """
        # create a member implicitely, if not already there
        #if hasattr(self.get_root(),'service_members'):
        #    self.get_root().service_members.get_member(
        #        self.REQUEST.AUTHENTICATED_USER.getUserName())

    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'get_xml')
    def get_xml(self, with_sub_publications=0, last_version=0):
        """Get XML-Document in UTF8-Encoding for object (recursively).

        Note that you get a full document with a processing instruction.
        if you want to get "raw" xml, use the 'to_xml' machinery.
        """
        context = XMLExportContext()
        context.f = StringIO()
        context.with_sub_publications = with_sub_publications
        context.last_version = not not last_version
        w = context.f.write
        # construct xml and return UTF8-encoded string
        w(u'<?xml version="1.0" encoding="UTF-8" ?>\n')
        w(u'<silva xmlns="%s" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xsi:schemaLocation="%s %s" '
            #'xml:base="%s" '
            'silva_root="%s" >' % (self._xml_namespace,
                self._xml_namespace, self._xml_schema,
            #    self.absolute_url(),
                self.getPhysicalRoot().absolute_url()))
        self.to_xml(context)
        w(u'</silva>')
        result = context.f.getvalue()
        return result.encode('UTF-8') 
    
    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'get_xml_for_objects')
    def get_xml_for_objects(self, objects, with_sub_publications=0, last_version=0):
        """Get XML-Document in UTF8-Encoding for a list of object references

        Note that you get a full document with a processing instruction.
        if you want to get "raw" xml, use the 'to_xml' machinery.
        """
        context = XMLExportContext()
        context.f = StringIO()
        context.with_sub_publications = with_sub_publications
        context.last_version = not not last_version
        w = context.f.write
        # construct xml and return UTF8-encoded string
        w(u'<?xml version="1.0" encoding="UTF-8" ?>\n')
        w(u'<silva xmlns="%s" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xsi:schemaLocation="%s %s">' % (self._xml_namespace,
                self._xml_namespace, self._xml_schema))
        for obj in objects:
            obj.to_xml(context)
        w(u'</silva>')
        result = context.f.getvalue()
        return result.encode('UTF-8') 
    
    security.declareProtected(SilvaPermissions.ApproveSilvaContent,
                              'to_xml') 
    def to_xml(self, context):
        """Handle unknown objects. (override in subclasses)
        """
        context.f.write('<unknown id="%s">%s</unknown>' % (self.id, self.meta_type))      
        
InitializeClass(SilvaObject)
