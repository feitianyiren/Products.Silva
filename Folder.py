# Zope
import Acquisition
from Acquisition import aq_inner
from OFS import Folder, SimpleItem
from AccessControl import ClassSecurityInfo
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
import Globals
# Silva
from ViewRegistry import ViewAttribute
from TocSupport import TocSupport
import Copying
import Interfaces
# misc
from helpers import add_and_edit

class Folder(TocSupport, Folder.Folder):
    """Silva Folder.
    """
    meta_type = "Silva Folder"

    __implements__ = Interfaces.TransparentContainer
    
    security = ClassSecurityInfo()

    # allow edit view on this object
    edit = ViewAttribute('edit')
    
    def __init__(self, id, title):
        self.id = id
        self._title = title
        self._toc_ids = []
        
    def __repr__(self):
        return "<Silva Folder instance at %s>" % self.id

    # MANIPULATORS
    def set_title(self, title):
        """Set the title of this folder.
        """
        self._title = title 
    
    # ACCESSORS

    def get_folder(self):
        """Get the folder an object is in. Can be used with
        acquisition to get the 'nearest' folder.
        """
        return self.aq_inner
    
    def folder_url(self):
        """Get url for folder.
        """
        return self.absolute_url()

    def title(self):
        """Get the title.
        """
        return self._title
    
    def is_published(self):
        """Return true if this is published."""
        #for item in self.objectValues(['Silva Folder', 'Silva Document']):
        #    if item.is_published():
        #        return 1            
        return 1
        
    def move_object_up(self, ref):
        """Move object up.
        """
        object = Copying.resolve_ref(self.getPhysicalRoot(), ref)
        folder = object.aq_parent.aq_inner
        # we can't move up anything not in _toc_ids
        toc_ids = folder._toc_ids
        if object.id not in toc_ids:
            return None
        # can't move up 'default'
        if object.id == 'default':
            return None
        # find position of object in toc_ids
        i = toc_ids.index(object.id)
        # can't move up something already on top
        if i == 0:
            return None
        # can't move above 'default'
        if i == 1 and toc_ids[0] == 'default':
            return None
        # now move up id
        toc_ids[i] = toc_ids[i - 1]
        toc_ids[i - 1] = object.id
        folder._toc_ids = toc_ids
        return 1
    
    def move_object_down(self, ref):
        """move object down.
        """
        object = Copying.resolve_ref(self.getPhysicalRoot(), ref)
        folder = object.aq_parent.aq_inner
        toc_ids = folder._toc_ids
        # can't move anything not in toc_ids
        if object.id not in toc_ids:
            return None
        # can't move down 'default'
        if object.id == 'default':
            return None
        # find position of object in folder
        i = toc_ids.index(object.id)
        # can't move down something already at bottom
        if i == len(toc_ids) - 1:
            return None
        # now move down id
        toc_ids[i] = toc_ids[i + 1]
        toc_ids[i + 1] = object.id
        folder._toc_ids = toc_ids
        return 1

    def get_contents(self):
        """Get list of contents of this folder.
        """
        return map(self._getOb, self._toc_ids)
        
    def get_tree(self):
        """Get flattened tree of contents.
        """
        l = []
        self._get_tree_helper(l, 0)
        return l

    def _get_tree_helper(self, l, indent):
        # make _toc_ids if we haven't got any
        toc_ids = getattr(self, '_toc_ids', None)
        # uncomment next lines to flush toc_ids attributes completely
        # (you'll lose order info too, though)
        #toc_ids = None
        # FIXME
        #if toc_ids is None:
        #    toc_ids = []
        #    for item in self.objectValues(['Silva Folder', 'Silva Document']):
        #        toc_ids.append(item.id)
        #    self._toc_ids = toc_ids
            
        # first sort items so that default is always the first item
        items = []
        first_item = None
        for id in toc_ids:
            # try to get item in toc_ids, skip anything that could not
            # be found (should really remove this from _toc_ids)
            item = getattr(self, id, None)
            if item is None:
                continue
            if id == 'default' and item.meta_type == 'Silva Document':
                first_item = item
            else:
                items.append(item)
        if first_item is not None:
            items.insert(0, first_item)
        # now add them to the main toc list
        for item in items:
            if Interfaces.TransparentContainer.isImplementedBy(item):
                l.append((indent, item))
                item._get_tree_helper(l, indent + 1)
            else:
                l.append((indent, item))

    def create_ref(self, obj):
        """Create a moniker for the object.
        """
        return Copying.create_ref(obj)

    def resolve_ref(self, ref):
        """Resolve reference to object.
        """
        return Copying.resolve_ref(self.getPhysicalRoot(), ref)
    
    def action_rename(self, ref, id, title):
        """Rename object moniker refers to.
        """
        object = Copying.resolve_ref(self.getPhysicalRoot(), ref)
        # first change id if necessary
        if object.id != id:
            parent = object.aq_inner.aq_parent
            parent.manage_renameObject(object.id, id)
        # now change title
        object.set_title(title)
    
    def action_delete(self, refs):
        """Delete objects monikers refer to.
        """
        Copying.delete(self.getPhysicalRoot(), refs)

    def action_cut(self, refs, REQUEST):
        """Cut objects.
        """
        Copying.cut(self.getPhysicalRoot(), refs, REQUEST)
        
    def action_copy(self, refs, REQUEST):
        """Copy objects.
        """
        Copying.copy(self.getPhysicalRoot(), refs, REQUEST)

    def action_paste(self, REQUEST):
        """Paste objects on clipboard.
        """
        if self.can_paste(REQUEST):
            Copying.paste(self, REQUEST=REQUEST)
    
    def action_paste_to(self, ref, REQUEST):
        """Paste objects on clipboard to ref.
        """
        obj = Copying.resolve_ref(self.getPhysicalRoot(), ref)
        obj.action_paste(REQUEST)

    def action_dedent(self, ref):
        """Dedent object.
        """
        # get object to dedent
        root = self.getPhysicalRoot()
        object = Copying.resolve_ref(root, ref)
        # folder we're dedenting from
        from_folder = object.aq_parent
        # folder we're dedenting to
        to_folder = from_folder.aq_parent
        # can't move to something that is not a normal folder
        if not Interfaces.Container.isImplementedBy(to_folder):
            return None
        # can't dedent anything not in _toc_ids
        toc_ids = from_folder._toc_ids
        if object.id not in toc_ids:
            return None
        # can't dedent 'default'
        if object.id == 'default':
            return None
        # now cut & paste object
        cb = Copying.cut(root, [ref])
        Copying.paste(to_folder, cb_copy_data=cb)
        # find position of from_folder in to_folder
        toc_ids = to_folder._toc_ids
        i = toc_ids.index(from_folder.id)
        # add object to toc_ids of to_folder,
        # just after position of from_folder
        toc_ids.remove(object.id)
        toc_ids.insert(i + 1, object.id)
        to_folder._toc_ids = toc_ids
        return 1
    
    def can_paste(self, REQUEST):
        """Can we paste what is in clipboard to this object?"""
        return 1
        
Globals.InitializeClass(Folder)

manage_addFolderForm = PageTemplateFile("www/folderAdd", globals(),
                                        __name__='manage_addFolderForm')

def manage_addFolder(self, id, title, create_default=1, REQUEST=None):
    """Add a Folder."""
    object = Folder(id, title)
    self._setObject(id, object)
    object = getattr(self, id)
    # add doc
    if create_default:
        object.manage_addProduct['Silva'].manage_addDocument('default', '')
    add_and_edit(self, id, REQUEST)
    return ''



