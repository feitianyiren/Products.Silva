from __future__ import nested_scopes
from ISilvaObject import ISilvaObject
from IContainer import IContainer
from IVersionedContent import IVersionedContent, ICatalogedVersionedContent
from IVersion import IVersion
from Membership import NoneMember, noneMember 

def from091to092(self, root):
    """Upgrade Silva content from 0.9.1 to 0.9.2
    """
    upgrade_using_registry(root, '0.9.2')

def from09to091(self, root):
    """Upgrade Silva from 0.9 to 0.9.1
    """
    # upgrade member objects in the site if they're still using the old system
    upgrade_memberobjects(root)
    # upgrade xml in the site
    upgrade_using_registry(root, '0.9.1')
    
def from086to09(self, root):
    """Upgrade Silva from 0.8.6(.1) to 0.9.
    """
    id = root.id
    # Put a copy of the current Silva Root in a backup folder.
    backup_id = id + '_086'
    self.manage_addFolder(backup_id)
    cb = self.manage_copyObjects([id])
    backup_folder = getattr(self, backup_id)
    backup_folder.manage_pasteObjects(cb_copy_data=cb)
    # Delete and re-install the DirectoryViews
    from install import add_fss_directory_view
    root.service_views.manage_delObjects(['Silva'])
    add_fss_directory_view(root.service_views, 'Silva', __file__, 'views')
    root.manage_delObjects([
        'globals', 'service_utils', 'service_widgets'])       
    add_fss_directory_view(root, 'globals', __file__, 'globals')
    add_fss_directory_view(root, 'service_utils', __file__, 'service_utils')
    add_fss_directory_view(root, 'service_widgets', __file__, 'widgets')

def from085to086(self, root):
    """Upgrade Silva from 0.8.5 to 0.8.6 as a simple matter of programming.
    """
    # rename silva root so we can drop in fresh new one
    id = root.id
    backup_id = id + '_085'
    self.manage_renameObject(id, backup_id)
    orig_root = getattr(self, backup_id)
    # create new silva root
    self.manage_addProduct['Silva'].manage_addRoot(id, orig_root.title)
    dest_root = getattr(self, id)
    # wipe out layout stuff from root as we're going to copy it over
    delete_ids = [obj.getId() for obj in dest_root.objectValues() if
                  obj.meta_type in ['DTML Method', 'Script (Python)', 'Page Template']]
    dest_root.manage_delObjects(delete_ids)

    # now copy over silva contents from old root; everything should be a
    # SilvaObject
    copy_ids = [obj.getId() for obj in orig_root.objectValues() if
                ISilvaObject.isImplementedBy(obj)]
    cb = orig_root.manage_copyObjects(copy_ids)
    dest_root.manage_pasteObjects(cb_copy_data=cb)

    # also copy over layout stuff and various services
    layout_ids = [obj.getId() for obj in orig_root.objectValues() if
                  obj.meta_type in ['DTML Method', 'Script (Python)', 'Page Template']  or \
                  obj.getId() in ('service_groups', 'service_files', 'service_mailhost', 'service_catalog') ]

    other_ids = [obj.getId() for obj in orig_root.objectValues() if
                 obj.meta_type not in ['DTML Method', 'Script (Python)', 'Page Template', \
                                       'Silva View Registry', 'XMLWidgets Editor Service', 'XMLWidgets Registry'] \
                 and obj.getId() not in ['globals', 'service_utils', 'service_setup', 'service_widgets', 'service_groups', 'service_files'] \
                 and not ISilvaObject.isImplementedBy(obj) ]

    
    cb = orig_root.manage_copyObjects(layout_ids)
    dest_root.manage_pasteObjects(cb_copy_data=cb)

    # now to copy over properties

    # figure out what changed
    dest_properties = dest_root.propertyIds()
    new_properties = []
    changed_properties = []
    for id in orig_root.propertyIds():
        if id in dest_properties:
            changed_properties.append(id)
        else:
            new_properties.append(id)
    # alter properties that need to be altered
    for id in changed_properties:
        dest_root.manage_changeProperties({id: orig_root.getProperty(id)})
    # add properties that need to be added
    for id in new_properties:
        dest_root.manage_addProperty(id, orig_root.getProperty(id),
                                     orig_root.getPropertyType(id))
    
    # now copy over the roles information
    if hasattr(orig_root, '__ac_local_roles__'):
        dest_root.__ac_local_roles__ = orig_root.__ac_local_roles__
    if hasattr(orig_root, '__ac_local_groups__'):
        dest_root.__ac_local_groups__ = orig_root.__ac_local_groups__

    # if there's an 'acl_users', 'images', or 'locals' copy that over as well.
    to_copy_ids = []
    for id in ['acl_users', 'images', 'locals']:
        if hasattr(orig_root.aq_base, id):
            to_copy_ids.append(id)
            if id in other_ids:
                other_ids.remove(id)
    cb = orig_root.manage_copyObjects(to_copy_ids)
    dest_root.manage_pasteObjects(cb_copy_data=cb)

    # copy over order information
    dest_root._ordered_ids = orig_root._ordered_ids
    
    # we still may not have everything, but a good part..
    # should advise the upgrader to copy over the rest by hand
    
    return other_ids

def upgrade_memberobjects(obj):
    service_members = obj.service_members
    for o in obj.aq_explicit.objectValues():
        info = getattr(o, '_last_author_info', None)
        if info is not None and type(info) == type({}):
            if info.has_key('uid'):
                o._last_author_info = service_members.get_cached_member(
                    info['uid'])
            else:
                o._last_author_info = noneMember
        if IContainer.isImplementedBy(o):
            upgrade_memberobjects(o)

def upgrade_using_registry(obj, version):
    """Upgrades obj recursively for a specific Silva version
    """
    for o in obj.objectValues():
        mt = o.meta_type
        if upgrade_registry.is_registered(mt, version):
            upgrade = upgrade_registry.get_meta_type(mt, version)(o)
        if IContainer.isImplementedBy(o):
            upgrade_using_registry(o, version)

def upgrade_list_titles_in_parsed_xml(top):
    for child in top.childNodes:
        if child.nodeName in ('list', 'nlist', 'dlist'):
            for list_child in child.childNodes:
                if list_child.nodeType == list_child.TEXT_NODE:
                    continue
                if list_child.nodeName == 'title':
                    data = ''
                    for data_child in list_child.childNodes:
                        data += data_child.data
                    list_child.parentNode.removeChild(list_child)
                    if data.strip() == '':
                        break
                    heading = list_child.ownerDocument.createElement(
                        u'heading')
                    heading_text = list_child.ownerDocument.createTextNode(
                        data)
                    heading.appendChild(heading_text)
                    heading.setAttribute(u'type', u'subsub')
                    child.parentNode.insertBefore(heading, child)
                    break
                elif list_child.nodeName != 'title':
                    break
        if child.nodeName == 'nlist':
            for list_child in child.childNodes:
                if list_child.nodeType == list_child.TEXT_NODE:
                    continue
                upgrade_list_titles_in_parsed_xml(list_child)
        if child.nodeName == 'image':
            if child.hasAttribute('image_path'):
                path = child.getAttribute('image_path')
                newpath = path
                try:
                    image = top.restrictedTraverse(path.split('/'))
                    newpath = '/'.join(image.getPhysicalPath())
                except:
                    if path[0] == '/':
                        try:
                            image = top.restrictedTraverse(path[1:].split('/'))
                            newpath = '/'.join(image.getPhysicalPath())
                        except:
                            newpath = path 
                child.removeAttribute('image_path')
                if child.hasAttribute('image_id'):
                     child.removeAttribute('image_id')
                child.setAttribute('path', newpath)
            elif child.hasAttribute('image_id'):
                id = child.getAttribute('image_id')
                # XXX somehow, this way the image is not found...
                image = getattr(top.get_container(), id, None)
                newpath = id
                if image:
                    newpath = unicode('/'.join(image.getPhysicalPath()))
                child.removeAttribute('image_id')
                child.setAttribute('path', newpath)
        if child.nodeName == 'table':
            for table_child in child.childNodes:
                if table_child.nodeType == table_child.TEXT_NODE:
                    continue
                if table_child.nodeName != 'row':
                    continue
                for field in table_child.childNodes:
                    if field.nodeType == field.TEXT_NODE:
                        continue
                    upgrade_list_titles_in_parsed_xml(field)
        
class UpgradeRegistry:
    """Here people can register upgrade methods for their objects
    """
    def __init__(self):
        self.__registry = {}
    
    def register(self, meta_type, upgrade_handler, version):
        """Register a meta_type for upgrade.

        The upgrade handler is called with the object as its only argument
        when the upgrade script encounters an object of the specified
        meta_type.
        """
        if self.__registry.has_key(meta_type) and self.__registry[meta_type].has_key(version):
            raise Exception, 'Meta type %s already registered for version %s!' % (meta_type, version)
        if not self.__registry.has_key(meta_type):
            self.__registry[meta_type] = {}
        self.__registry[meta_type][version] = upgrade_handler

    def get_meta_type(self, meta_type, version):
        """Return the registered upgrade_handler of meta_type
        """
        return self.__registry[meta_type][version]

    def is_registered(self, meta_type, version):
        """Returns whether the meta_type is registered"""
        return self.__registry.has_key(meta_type) and self.__registry[meta_type].has_key(version)

upgrade_registry = UpgradeRegistry()

#-----------------------------------------------------------------------------
# Upgrade functions using the upgrade registry
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# 0.9 to 0.9.1
#-----------------------------------------------------------------------------

# Some upgrade stuff
def upgrade_document_091(obj):
    for o in obj.objectValues():
        if o.meta_type == 'Silva Document Version':
            upgrade_list_titles_in_parsed_xml(o.content.documentElement)

def upgrade_demoobject_091(obj):
    for o in obj.objectValues():
        if o.meta_type == 'Silva DemoObject Version':
            upgrade_list_titles_in_parsed_xml(o.content.documentElement)

upgrade_registry.register('Silva Document', upgrade_document_091, '0.9.1')
upgrade_registry.register('Silva DemoObject', upgrade_demoobject_091, '0.9.1')

#-----------------------------------------------------------------------------
# 0.9.1 to 0.9.2
#-----------------------------------------------------------------------------

# convert old style documents (with ParsedXML as version) to new style ones (where
# ParsedXML is an attribute of Version)
def convert_document_092(obj):
    from StringIO import StringIO
    from random import randrange
    from string import lowercase
    from DateTime import DateTime

    for version in ['unapproved', 'approved', 'public', 'last_closed']:
        v = getattr(obj, 'get_%s_version' % version)()
        if v is not None and not hasattr(getattr(obj, v), 'documentElement'):
            return

    parent = obj.aq_parent.aq_inner
    
    # first copy self to some other name
    # create some unique id
    oldid = obj.id
    uniqueid = ''
    while 1:
        uniqueid += lowercase[randrange(len(lowercase))]
        if len(uniqueid) > 4 and uniqueid not in parent.objectIds():
            break

    parent.manage_renameObject(obj.id, uniqueid)
    parent.manage_addProduct['Silva'].manage_addDocument(oldid, obj.get_title())

    newobj = getattr(parent, oldid)
    
    # we're going to have to do this from old to new: first the last
    # closed, then the public, the approved and last the unapproved 
    # versions. This way we can use Silva's version machinery without any 
    # problems.

    # set the id to use for creating new versions, should start at 1 'cause there
    # already is the one that's created when creating a document
    current_id = 1
    
    # we copy the last closed version because of the newly added revert
    # machinery, the rest of the closed versions we skip since we don't
    # have any use for them anyway. The user should be warned about this
    # though!

    def get_version_xml(obj, version):
        v = getattr(obj, version, None)
        if v is None:
            raise Exception, 'No version %s!' % version
        s = StringIO()
        v.documentElement.writeStream(s)
        return s.getvalue().encode('UTF8')
    
    last_closed = obj.get_last_closed_version()
    if last_closed is not None:
        xml = get_version_xml(obj, last_closed)
        newobj.set_unapproved_version_publication_datetime(DateTime() - 1)
        newobj.set_unapproved_version_expiration_datetime(DateTime() - 1)
        newobj.approve_version() # should be closed directly because of expiration date
        getattr(newobj, newobj.get_last_closed_version()).content.manage_edit(xml)
        newobj.manage_addProduct['Silva'].manage_addDocumentVersion(str(current_id), '')
        newobj.create_version(str(current_id), None, None)
        current_id += 1
    public = obj.get_public_version()
    if public is not None:
        xml = get_version_xml(obj, public)
        newobj.set_unapproved_version_publication_datetime(
                obj.get_public_version_publication_datetime())
        newobj.set_unapproved_version_expiration_datetime(
                obj.get_public_version_expiration_datetime())
        newobj.approve_version()
        getattr(newobj, newobj.get_public_version()).content.manage_edit(xml)
        newobj.manage_addProduct['Silva'].manage_addDocumentVersion(str(current_id), '')
        newobj.create_version(str(current_id), None, None)
        current_id += 1
    approved = obj.get_approved_version()
    if approved is not None:
        xml = get_version_xml(obj, approved)
        newobj.set_unapproved_version_publication_datetime(
                obj.get_approved_version_publication_datetime())
        newobj.set_unapproved_version_expiration_datetime(
                obj.get_approved_version_expiration_datetime())
        newobj.approve_version()
        getattr(newobj, newobj.get_approved_version()).content.manage_edit(xml)
        newobj.manage_addProduct['Silva'].manage_addDocumentVersion(str(current_id), '')
        newobj.create_version(str(current_id), None, None)
        current_id += 1
    unapproved = obj.get_unapproved_version()
    if unapproved is not None:
        xml = get_version_xml(obj, unapproved)
        newobj.set_unapproved_version_publication_datetime(
                obj.get_unapproved_version_publication_datetime())
        newobj.set_unapproved_version_expiration_datetime(
                obj.get_unapproved_version_expiration_datetime())
        getattr(newobj, str(newobj.get_unapproved_version())).content.manage_edit(xml)

    
    parent.manage_delObjects([uniqueid])
    
upgrade_registry.register('Silva Document', convert_document_092, '0.9.2')
