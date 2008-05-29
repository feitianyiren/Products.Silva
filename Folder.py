# Copyright (c) 2002-2008 Infrae. All rights reserved.
# See also LICENSE.txt
# $Revision: 1.180 $

from zope.interface import implements
from zope.i18n import translate

# Zope
from OFS import Folder, SimpleItem
from AccessControl import ClassSecurityInfo, getSecurityManager
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Globals import InitializeClass
from OFS.CopySupport import _cb_decode, _cb_encode # HACK
from Products.ZCatalog.CatalogPathAwareness import CatalogPathAware
from zExceptions import InternalError
import transaction
# Silva
from Products.Silva.Ghost import ghostFactory, canBeHaunted
from Products.Silva.ExtensionRegistry import extensionRegistry
from SilvaObject import SilvaObject
from Publishable import Publishable
import Copying
import SilvaPermissions
import ContainerPolicy
import validate
# misc
import helpers
import re
import urllib
from sys import exc_info

from Products.Silva.ImporterRegistry import get_importer, xml_import_helper
from Products.Silva.ImporterRegistry import get_xml_id, get_xml_title
from Products.Silva.Metadata import export_metadata
from Products.Silva.File import file_factory
from Products.Silva import mangle
from Products.Silva.i18n import translate as _
from Products.ParsedXML.ParsedXML import ParsedXML
from Products.ParsedXML.ParsedXML import createDOMDocument
from Products.ParsedXML.ExtraDOM import writeStream

from adapters.interfaces import IContentImporter
from interfaces import IPublishable, IContent, IGhost
from interfaces import IVersionedContent, ISilvaObject, IAsset
from interfaces import IContainer, IFolder, IPublication, IRoot

from ContentObjectFactoryRegistry import contentObjectFactoryRegistry
from zExceptions import Forbidden, MethodNotAllowed

class Folder(CatalogPathAware, SilvaObject, Publishable, Folder.Folder):
    __doc__ = _("""The presentation of the information within a
       publication is structured with folders. They determine the visual
       hierarchy that a Visitor sees. Folders on the top level
       define sections of a publication, subfolders define chapters, etc.
       Note that unlike publications, folders are transparent, meaning you
       can see through them in the sidebar tree navigation and the Publish 
       screen.
    """)
    security = ClassSecurityInfo()

    meta_type = "Silva Folder"

    default_catalog = 'service_catalog'

    object_type = 'container'

    # A hackish way to get a Silva tab in between the standard ZMI tabs
    inherited_manage_options = Folder.Folder.manage_options
    manage_options=(
        (inherited_manage_options[0], ) +
        ({'label':'Silva /edit...', 'action':'edit'}, ) +
        inherited_manage_options[1:]
        )

    _allow_feeds = False

    used_space = 0

    implements(IFolder)
        
    def __init__(self, id):
        Folder.inheritedAttribute('__init__')(
            self, id)
        self._ordered_ids = []

    #overridden from ObjectManager, so that additional filtering
    #can be done to remove those objects that aren't zmi-addable
    #(see the doc/developer_changes notes for more info)
    def filtered_meta_types(self, user=None):
        mt = Folder.inheritedAttribute('filtered_meta_types')(self, user)
        newm = []
        for m in mt:
            cf = m['container_filter']
            #If the container_filter is the specail filter for
            #Silva content types, then call it to see if that type
            #should be filtered from the zmi-add list as well
            if cf and cf.__name__=="SilvaZCMLContainerFilter" \
                   and not cf(self, filter_addable=True):
                continue
            newm.append(m)
        return newm

    def _invalidate_sidebar(self, item):
        # invalidating sidebar also takes place for folder when index gets
        # changed
        if item.id == 'index':
            item = item.get_container()
        if not IContainer.providedBy(item):
            return
        service_sidebar = self.aq_inner.service_sidebar
        service_sidebar.invalidate(item)
        if (IPublication.providedBy(item) and 
                not IRoot.providedBy(item)):
            service_sidebar.invalidate(item.aq_inner.aq_parent)

    # MANIPULATORS

    security.declarePrivate('titleMutationTrigger')
    def titleMutationTrigger(self):
        """This trigger is called upon save of Silva Metadata. More
        specifically, when the silva-content - defining titles - set is 
        being editted for this object.
        """
        self._invalidate_sidebar(self)
        
    security.declareProtected(SilvaPermissions.ChangeSilvaContent,
                              'move_object_up')
    def move_object_up(self, id):
        """Move object up. Returns true if move succeeded.
        """
        ids = self._ordered_ids
        try:
            i = ids.index(id)
        except ValueError:
            return 0
        if i == 0:
            return 0
        self._invalidate_sidebar(getattr(self, id))
        ids[i], ids[i - 1] = ids[i - 1], ids[i]
        self._ordered_ids = ids
        return 1

    security.declareProtected(SilvaPermissions.ChangeSilvaContent,
                              'move_object_down')
    def move_object_down(self, id):
        """move object down.
        """
        ids = self._ordered_ids
        try:
            i = ids.index(id)
        except ValueError:
            return 0
        if i == len(ids) - 1:
            return 0
        self._invalidate_sidebar(getattr(self, id))
        ids[i], ids[i + 1] = ids[i + 1], ids[i]
        self._ordered_ids = ids
        return 1

    security.declareProtected(SilvaPermissions.ChangeSilvaContent,
                              'move_to')
    def move_to(self, move_ids, index):
        ids = self._ordered_ids
        # check whether all move_ids are known
        for move_id in move_ids:
            if move_id not in ids:
                return 0
        for id in move_ids:
            if ids.index(id) < index:
                index += 1
                break
        ids_without_moving_ids = []
        move_ids_in_order = []
        for id in ids:
            if id in move_ids:
                move_ids_in_order.append(id)
                ids_without_moving_ids.append(None)
            else:
                ids_without_moving_ids.append(id)
        ids = ids_without_moving_ids
        move_ids = move_ids_in_order
        move_ids.reverse()
        for move_id in move_ids:
            self._invalidate_sidebar(getattr(self, move_id))
            ids.insert(index, move_id)
        ids = [id for id in ids if id is not None]
        self._ordered_ids = ids
        return 1

    def _add_ordered_id(self, item):
        """Add item to the end of the list of ordered ids.
        """
        # this already happens to do what we want
        # this works in case of active objects that were added
        # (they're added to the list of ordered ids)
        # and also for inactive objects
        # (they're not added to the list; nothing happens)
        if not IPublishable.providedBy(item):
            return
        if IContent.providedBy(item) and item.is_default():
            return
        ids = self._ordered_ids
        id = item.id
        if id not in ids:
            ids.append(id)
            self._ordered_ids = ids
            self._p_changed = 1
        
    def _remove_ordered_id(self, item):
        if not IPublishable.providedBy(item):
            return
        if IContent.providedBy(item) and item.is_default():
            return
        ids = self._ordered_ids
        if item.id in ids:
            ids.remove(item.id)
            self._ordered_ids = ids
            self._p_changed = 1

    security.declareProtected(SilvaPermissions.ApproveSilvaContent, 
                              'refresh_active_publishables')
    def refresh_active_publishables(self):
        """Clean up all ordered ids in this container and all subcontainers.
        This method normally does not need to be called, but if something is
        wrong, this can be called in emergency situations. WARNING: all
        ordering information is lost!
        """
        ids = []
        for object in self.objectValues():
            if not IPublishable.providedBy(object):
                continue
            if IContent.providedBy(object) and object.is_default():
                continue
            ids.append(object.id)
            if IContainer.providedBy(object):
                object.refresh_active_publishables()
        self._ordered_ids = ids

    security.declareProtected(SilvaPermissions.ChangeSilvaContent,
                              'action_rename')
    def action_rename(self, orig_id, new_id):
        """Change id of object with id orig_id.
        """
        # check if new_id is valid
        if not mangle.Id(self, new_id, 
                instance=getattr(self, orig_id)).isValid():
            return
        # check if renaming (which in essence is the deletion of a url)
        # is allowed
        if not self.is_delete_allowed(orig_id):
            return
        # only change id if necessary
        if orig_id == new_id:
            return
        oids = self._ordered_ids
        try:
            publishable_id = oids.index(orig_id)
        except ValueError:
            # this is not a clean fix but it should work; items like
            # assets can be renamed but are not in the ordered_ids.
            # therefore trying to move them doesn't work, and just ignore
            # that.
            publishable_id = None
        self.manage_renameObject(orig_id, new_id)
        if publishable_id is not None:
            self.move_to([new_id], publishable_id)
        return 1

    security.declareProtected(SilvaPermissions.ChangeSilvaContent,
                              'action_delete')
    def action_delete(self, ids):
        """Delete objects.
        """
        # check whether deletion is allowed
        deletable_ids = [id for id in ids if self.is_delete_allowed(id)]
        self.manage_delObjects(deletable_ids)

    security.declareProtected(SilvaPermissions.ChangeSilvaContent,
                              'action_cut')
    def action_cut(self, ids, REQUEST):
        """Cut objects.
        """
        # check whether deletion is allowed
        deletable_ids = [id for id in ids if self.is_delete_allowed(id)]
        # FIXME: need to do unit tests for this
        # FIXME: would this lead to a sensible user interface?
        if len(deletable_ids) > 0:
          self.manage_cutObjects(deletable_ids, REQUEST)
        
    security.declareProtected(SilvaPermissions.ReadSilvaContent,
                              'action_copy')
    def action_copy(self, ids, REQUEST):
        """Copy objects.
        """
        self.manage_copyObjects(ids, REQUEST)
        
    security.declareProtected(SilvaPermissions.ChangeSilvaContent,
                              'action_paste')
    def action_paste(self, REQUEST):
        """Paste objects on clipboard.

            Note: the return value of this method has changed in Silva 1.2
        """
        # HACK
        # determine if we're cut-paste or copy-pasting, wish we
        # didn't have to..
        if not REQUEST.has_key('__cp') or REQUEST['__cp'] is None:
            return
        op, ref = _cb_decode(REQUEST['__cp'])

        # copy-paste operation
        # items on clipboard should be unapproved & closed, but
        # only the *copies*
        # (actually in case of a cut-paste the original
        # should not be approved, too)
        messages = []
        message_type = 'feedback'
        paths = []
        for item in self.cb_dataItems():
            if ((op == 0 or item.get_container().is_delete_allowed(item.id)) 
                    and item.meta_type in [addable['name'] for 
                        addable in self.get_silva_addables()]):
                paths.append(item.getPhysicalPath())
            elif item.meta_type not in [addable['name'] for 
                    addable in self.get_silva_addables()]:
                msg = _(('pasting &#xab;${id}&#xbb; is not allowed in '
                         'this type of container'), mapping={'id': item.id})
                messages.append(translate(msg))
                message_type = 'error'

        if len(paths) == 0:
            return message_type, ', '.join(messages).capitalize()
        
        # now we do the paste
        # encode the paths the way they came in, without the removed items
        # however, the result is a list of mappings with 'new_id' as
        # one of the keys
        result = self.manage_pasteObjects(_cb_encode((op, paths)))

        # now unapprove & close everything just pasted
        # first get the newly pasted ids
        paste_ids = [i['new_id'] for i in result]
        for paste_id in paste_ids:
            object = getattr(self, paste_id)
            helpers.unapprove_close_helper(object)
            object.sec_update_last_author_info()
            msg = _('pasted &#xab;${id}&#xbb;', mapping={'id': paste_id})
            messages.append(translate(msg))
        
        # on cut/paste, clear the clipboard when done
        if op == 1:
            REQUEST['__cp'] = None

        return message_type, ', '.join(messages).capitalize()
            
    security.declareProtected(SilvaPermissions.ChangeSilvaContent,
                              'action_paste_to_ghost')
    def action_paste_to_ghost(self, REQUEST):
        """Paste what is on clipboard to ghost.

            Note: the return value of this method has changed in Silva 1.2
        """
        # create ghosts for each item on clipboard
        allowed_meta_types = [addable['name'] for 
            addable in self.get_silva_addables()]
        messages = []
        message_type = 'feedback'
        for item in self.cb_dataItems():
            if item.meta_type in allowed_meta_types:
                ids = self.objectIds()
                paste_id = item.id
                # keep renaming them until they have a unique id, the Zope way
                i = 0
                org_paste_id = paste_id
                while paste_id in ids:
                    i += 1
                    add = ''
                    if i > 1:
                        add = str(i)
                    if canBeHaunted(item):
                        paste_id = 'ghost%s_of_%s' % (add, org_paste_id)
                    else:
                        paste_id = 'copy%s_of_%s' % (add, org_paste_id)
                self._ghost_paste(paste_id, item, REQUEST)
                msg = _('pasted &#xab;${id}&#xbb;', mapping={'id': paste_id})
                messages.append(translate(msg))
            else:
                msg = _(('pasting &#xab;${id}&#xbb; is not allowed in '
                         'this type of container'), mapping={'id': item.id})
                messages.append(translate(msg))
                message_type = 'error'
        return message_type, ', '.join(messages).capitalize()

    def _ghost_paste(self, paste_id, item, REQUEST):
        if canBeHaunted(item):
            ghost = ghostFactory(self, paste_id, item)
            if ghost.meta_type == 'Silva Ghost Folder':
                ghost.haunt()
        elif IGhost.providedBy(item):
            content_url = item.get_haunted_url()
            item._factory(self, paste_id, content_url)
        else:
            # this is an object that just needs to be copied
            item = item._getCopy(self)
            item._setId(paste_id)
            self._setObject(paste_id, item)

    security.declareProtected(SilvaPermissions.ApproveSilvaContent,
                              'set_allow_feeds')
    def set_allow_feeds(self, allow):
        """change the flag that indicates whether rss/atom feeds are allowed
        on this container"""
        self._allow_feeds = allow
        
    security.declareProtected(SilvaPermissions.ApproveSilvaContent,
                              'to_publication')
    def to_publication(self):
        """Turn this folder into a publication.
        """
        self._to_folder_or_publication_helper(to_folder=0)

    def _to_folder_or_publication_helper(self, to_folder):
        if to_folder:
            sc = helpers.SwitchClass(Folder)
        else:
            # to publication
            from Products.Silva.Publication import Publication
            sc = helpers.SwitchClass(Publication)
        return sc.upgrade(self)
        

    def _verify_quota(self):
        # Hook to check quota. Do nothing by default.
        pass

    security.declareProtected(SilvaPermissions.ChangeSilvaContent,
                              'update_quota')
    def update_quota(self, delta):

        if IContentImporter.providedBy(self.aq_parent):
            self.aq_inner.update_quota(delta)
            return

        self.used_space += delta
        if delta > 0:           # If we add stuff, check we're not
                                # over quota.
            self._verify_quota()

        if not IRoot.providedBy(self):
            self.aq_parent.update_quota(delta)



    # ACCESSORS
    
    security.declareProtected(
        SilvaPermissions.ReadSilvaContent, 'can_set_title')    
    def can_set_title(self):
        """Check to see if the title can be set by user, meaning:
        * he is Editor/ChiefEditor/Manager, or
        * he is Author _and_ the Folder does not contain published content
          or approved content recursively (self.is_published()).
        """
        user = getSecurityManager().getUser()
        if user.has_permission(SilvaPermissions.ApproveSilvaContent, self):
            return 1
        
        return not self.is_published() and not self.is_approved()

    security.declareProtected(SilvaPermissions.ReadSilvaContent,
                              'get_silva_addables')
    def get_silva_addables(self):
        """Get a list of addable Silva objects.
        """
        result = []
        allowed = self.get_silva_addables_allowed()
        for addable_dict in extensionRegistry.get_addables():
            meta_type = addable_dict['name']
            if allowed and meta_type not in allowed:
                continue
            if (self._is_silva_addable(addable_dict) and
                addable_dict['instance']._is_allowed_in_publication):
                # add the docstring to the dict so it is available 
                # in pythonscripts
                addable_dict['doc'] = addable_dict['instance'].__doc__
                result.append(addable_dict)
        return result

    security.declareProtected(SilvaPermissions.ReadSilvaContent,
                              'get_silva_addables_all')
    def get_silva_addables_all(self):
        result = [addable_dict['name']
                  for addable_dict in extensionRegistry.get_addables()
                  if self._is_silva_addable(addable_dict)]
        return result

    def _is_silva_addable(self, addable_dict):
        """Given a dictionary from filtered_meta_types, check whether this
        specifies a silva addable.
        """
        return (
            addable_dict.has_key('instance') and
            ISilvaObject.implementedBy(
            addable_dict['instance']) and
            not self.get_root().is_silva_addable_forbidden(
            addable_dict['name']) and
            self.service_view_registry.has_view('add', addable_dict['name'])
            )

    security.declareProtected(SilvaPermissions.ReadSilvaContent,
                              'get_silva_addables_allowed')
    def get_silva_addables_allowed(self):
        secman = getSecurityManager()
        addables = self.get_silva_addables_allowed_in_publication()
        allowed = [name for name in addables if secman.checkPermission('Add %ss' % name, self)]
        return allowed

    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'get_container')
    def get_container(self):
        """Get the container an object is in. Can be used with
        acquisition to get the 'nearest' container.
        FIXME: currently the container of a container is itself. Is this the 
        right behavior? It leads to subtle bugs..
        """
        return self.aq_inner

    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'get_real_container')
    def get_real_container(self):
        """Get the container, even if we're a container.

        If we're the root object, returns None.
        
        Can be used with acquisition to get the 'nearest' container.
        """
        container = self.get_container()
        if container is self:
            return container.aq_parent.get_container()
        return container
    
    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'container_url')
    def container_url(self):
        """Get url for container.
        """
        return self.absolute_url()

    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'allow_feeds')
    def allow_feeds(self):
        """return the flag that indicates whether rss/atom feeds are allowed
        on this container"""
        return self._allow_feeds
    
    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'is_transparent')
    def is_transparent(self):
        return 1

    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'is_published')
    def is_published(self):
        # Folder is published if its default document is published, or,
        # when no default document exists, if any of the objects it contains
        # are published.
        default = self.get_default()
        if default:
            if default.aq_explicit.is_published():
                return 1
            else:
                return 0
        for object in self.get_ordered_publishables():        
            if object.is_published():
                return 1
        return 0

    security.declareProtected(SilvaPermissions.ReadSilvaContent,
                              'is_approved')
    def is_approved(self):
        # Folder is approved if anything inside is approved
        default = self.get_default()
        if default and self.get_default().is_approved():
            return 1
        for object in self.get_ordered_publishables():        
            if object.is_approved():
                return 1
        return 0

    security.declareProtected(SilvaPermissions.ReadSilvaContent,
                              'is_delete_allowed')
    def is_delete_allowed(self, id):
        """Delete is only allowed if the object with id:
           - does not have an approved version
           - does not have a published version
           - if it is a container, does not contain anything of the
             above, recursively
        """
        object = getattr(self, id)
        return object.is_deletable()

    def is_deletable(self):
        """deletable if all containing objects are deletable

            NOTE: this will be horribly slow for large trees
        """
        default = self.get_default()
        if default and not default.is_deletable():
            return 0
        for object in self.get_ordered_publishables():
            if not object.is_deletable():
                return 0
        return 1
        

    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'get_default')
    def get_default(self):
        """Get the default content object of the folder.
        """
        if not hasattr(self.aq_base, 'index'):
            return None
        else:
            return getattr(self, 'index')

    security.declareProtected(
        SilvaPermissions.AccessContentsInformation, 'get_default_viewable')
    def get_default_viewable(self):
        """Get the viewable version of the default content object
        of this container.
        """
        # Returns None if there's no default, or the default has no
        # viewable version.
        default = self.get_default()
        if default is None:
            return None
        return default.get_viewable()
    
    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'get_modification_datetime')
    def get_modification_datetime(self, update_status=1):
        """Folders don't really have a modification datetime.
        """
        return self.service_metadata.getMetadataValue(
            self, 'silva-extra', 'modificationtime')
    
    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'get_ordered_publishables')
    def get_ordered_publishables(self):
        return map(self._getOb, self._ordered_ids)

    security.declareProtected(SilvaPermissions.ReadSilvaContent,
                              'get_silva_asset_types')
    def get_silva_asset_types(self):
        result = [addable_dict['name']
                  for addable_dict in extensionRegistry.get_addables()
                    if IAsset.implementedBy(addable_dict['instance'])]
        return result

    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'get_assets')
    def get_assets(self):
        result = []
        for object in self.objectValues(self.get_silva_asset_types()):
            result.append(object)
        result.sort(lambda x,y: cmp(x.getId(), y.getId()))
        return result

    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'get_other_content')
    def get_other_content(self):
        result = []
        assets = self.get_assets()
        publishables = self.get_ordered_publishables()
        default = self.get_default()
        for object in self.objectValues():
            if object in publishables:
                continue
            if object in assets:
                continue
            if object == default:
                continue
            result.append(object)
        result.sort(lambda x,y: cmp(x.getId(), y.getId()))
        return result
    
    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'get_assets_of_type')
    def get_assets_of_type(self, meta_type):
        result = []
        assets = self.get_assets()
        for object in assets:
            if object.meta_type == meta_type:
                result.append(object)
        return result

    # FIXME: what if the objects returned are not accessible with my
    # permissions? unlikely as my role is acquired?
    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'get_tree')
    def get_tree(self, depth=-1):
        """Get flattened tree of contents.
        The 'depth' argument limits the number of levels, defaults to unlimited
        """
        l = []
        self._get_tree_helper(l, 0, depth)
        return l

    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'get_container_tree')
    def get_container_tree(self, depth=-1):
        l = []
        self._get_container_tree_helper(l, 0, depth)
        return l

    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'get_public_tree')
    def get_public_tree(self, depth=-1):
        """Get flattened tree with public content, excluding subpublications.
        The 'depth' argument limits the number of levels, defaults to unlimited
        """
        l = []
        self._get_public_tree_helper(l, 0, depth)
        return l

    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'get_public_tree_all')
    def get_public_tree_all(self, depth=-1):
        """Get flattened tree with public content, including subpublications.
        The 'depth' argument limits the number of levels, defaults to unlimited
        """
        l = []
        self._get_public_tree_helper(l, 0, depth, 1)
        return l


    security.declareProtected(SilvaPermissions.AccessContentsInformation,
                              'get_status_tree')
    def get_status_tree(self, depth=-1):
        '''get Silva tree'''
        l = []
        self._get_status_tree_helper(l, 0, depth)
        return l

    def _get_tree_helper(self, l, indent, depth):
        for item in self.get_ordered_publishables():
            if item.getId() == 'index':
                # default document should not be inserted
                continue
            if (IContainer.providedBy(item) and
                item.is_transparent()):
                l.append((indent, item))
                if depth == -1 or indent < depth:
                    item._get_tree_helper(l, indent + 1, depth)
            else:
                l.append((indent, item))

    def _get_container_tree_helper(self, l, indent, depth):
        for item in self.get_ordered_publishables():
            if not IContainer.providedBy(item):
                continue
            if item.is_transparent():
                l.append((indent, item))
                if depth == -1 or indent < depth:
                    item._get_container_tree_helper(l, indent + 1, depth)
            else:
                l.append((indent, item))

    def _get_public_tree_helper(self, l, indent, depth, include_non_transparent_containers=0):
        for item in self.get_ordered_publishables():
            if not item.is_published():
                continue
            if self.service_toc_filter.filter(item):
                continue
            if (IContainer.providedBy(item) and
                (item.is_transparent() or include_non_transparent_containers)):
                l.append((indent, item))
                if depth == -1 or indent < depth:
                    item._get_public_tree_helper(l, indent + 1, depth, include_non_transparent_containers)
            else:
                l.append((indent, item))

    def _get_status_tree_helper(self, l, indent, depth):
        if IContainer.providedBy(self):
            default = self.get_default()
            if default is not None:
                l.append((indent, default))

        for item in self.get_ordered_publishables():
            l.append((indent, item))
            if not IContainer.providedBy(item):
                continue
            if (depth == -1 or indent < depth) and item.is_transparent():
                item._get_status_tree_helper(l, indent+1, depth)

    def create_ref(self, obj):
        """Create a moniker for the object.
        """
        return Copying.create_ref(obj)

    def resolve_ref(self, ref):
        """Resolve reference to object.
        """
        return Copying.resolve_ref(self.getPhysicalRoot(), ref)

    security.declareProtected(SilvaPermissions.ReadSilvaContent,
                              'to_xml')
    def to_xml(self, context):
        """Render object to XML.
        """
        f = context.f
        f.write('<silva_folder id="%s">' % self.id)
        self._to_xml_helper(context)
        export_metadata(self, context)
        f.write('</silva_folder>')

    def _to_xml_helper(self, context):
        if context.last_version:
            title = self.get_title_editable()
        else:
            title = self.get_title()
            
        context.f.write('<title>%s</title>' % helpers.translateCdata(title))
        default = self.get_default()
        if default is not None:
            default.to_xml(context)
        for object in self.get_ordered_publishables():
            if (IPublication.providedBy(object) and 
                    not context.with_sub_publications):
                continue
            object.to_xml(context)
        #for object in self.get_assets():
        #    pass

    security.declareProtected(SilvaPermissions.ChangeSilvaContent,
                              'xml_validate')
    def xml_validate(self, xml):
        """Return true if XML is valid.
        """
        return validate.validate(xml)
    
    security.declareProtected(SilvaPermissions.ChangeSilvaContent, 
        'xml_import')
    def xml_import(self, xml):
        """Import XML"""
        dom = createDOMDocument(xml)
        import_root = dom.documentElement
        if import_root.nodeName == u'silva':
            import_root = import_root.firstChild
        while import_root:
            # since some exceptions raised are strings or so, we're going to
            # convert them to 'Exception' here
            try:
                xml_import_helper(self, import_root)
            except Exception:
                raise
            except:
                obj, info, tb = exc_info()
                raise Exception, info, tb
            import_root = import_root.nextSibling

    security.declarePublic('url_encode')
    def url_encode(self, string):
        """A wrapper for the urllib.quote function
        
        to be used in Python scripts and PT's
        """
        return urllib.quote(string)

    security.declarePublic('url_decode')
    def url_decode(self, string):
        """A wrapper for the urllib.unquote_plus function"""
        return urllib.unquote_plus(string)

    # WebDAV
    security.declareProtected(SilvaPermissions.ChangeSilvaContent,
                                'manage_FTPget')
    def manage_FTPget(self):
        """Overridden because it should raise an exception rather then returning
            the contents of the index"""
        raise MethodNotAllowed

    manage_DAVget = manage_FTPget

    security.declarePrivate('MKCOL_handler')
    def MKCOL_handler(self, name):
        """WebDAV - create a sub folder"""
        name = self.url_decode(name)
        if not mangle.Id(self, name).isValid():
            raise Forbidden, 'folder id not valid'
        self.manage_addProduct['Silva'].manage_addFolder(name, name, create_default=1)

    security.declarePrivate('PUT_factory')
    def PUT_factory(self, name, content_type, body):
        """WebDAV PUT - create a sub object"""
        ret = None
        ct = content_type
        # XXX nastyness galore! our dear Zope throws in a stringified dict 
        # sometimes...
        try:
            ct = eval(content_type)['Content-Type']
        except NameError:
            pass
        
        # use the contentObjectFactoryRegistry (what a name!) to get
        # an object (if possible, else an InternalError will get raised)
        object = contentObjectFactoryRegistry.getObjectFor(self, name, ct, body)
        return object
                
InitializeClass(Folder)

def manage_addFolder(
    context, id, title, create_default=1, policy_name='None', REQUEST=None):
    """Add a Folder."""

    if not mangle.Id(context, id).isValid():
        return
    folder = Folder(id)
    context._setObject(id, folder)
    folder = getattr(context, id)
    folder.set_title(title)
    if create_default:
        policy = context.service_containerpolicy.getPolicy(policy_name)
        policy.createDefaultDocument(folder, title)
    helpers.add_and_edit(context, id, REQUEST)
    return ''

def xml_import_handler(object, node, factory=None):
    """Helper for importing folder objects into an other object"""

    def default_factory(object, id, title):
        object.manage_addProduct["Silva"].manage_addFolder(id, title, 0)
    
    id = get_xml_id(node)
    title = get_xml_title(node)
    id = str(mangle.Id(object, id).unique())
    if factory is None:
        factory = default_factory
    assert callable(factory), "Factory is not callable"
    factory(object, id, title)
    newfolder = getattr(object, id)
    for child in node.childNodes:
        if get_importer(child.nodeName):
            xml_import_helper(newfolder, child)
        elif (child.nodeName != u'title' and 
                hasattr(newfolder, 'set_%s' % child.nodeName) and 
                child.childNodes[0].nodeValue):
            getattr(newfolder, 'set_%s' % child.nodeName)(
                                    child.childNodes[0].nodeValue)

    return newfolder

## def object_will_be_moved(object, event):
##     if object != event.object:
##         return
##     event.oldParent._invalidate_sidebar(object)


def folder_moved_update_quota(obj, event):
    if obj != event.object:
        return
    if IRoot.providedBy(obj):
        return                  # Root is being destroyed, we don't
                                # care about quota anymore.
    if event.newParent is event.oldParent: # For rename event, we
                                           # don't need to do
                                           # something.
        return

    context = event.newParent or event.oldParent
    if not context.service_extensions.get_quota_subsystem_status():
        return

    size = obj.used_space
    if not size:
        return
    if event.oldParent:
        event.oldParent.update_quota(-size)
    if event.newParent:
        event.newParent.update_quota(size)

