# Zope
import Acquisition
from Acquisition import ImplicitAcquisitionWrapper, aq_base, aq_inner
from OFS import Folder, SimpleItem, ObjectManager
from AccessControl import ClassSecurityInfo
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
import Globals
# misc
from helpers import add_and_edit

class ViewRegistry(Folder.Folder):
    """Silva View Registry.
    """
    meta_type = "Silva View Registry"

    security = ClassSecurityInfo()

    manage_options = (
        ( {'label':'Contents', 'action':'manage_main'},
          {'label':'Associations', 'action':'manage_associationsForm'},
          {'label':'Security', 'action':'manage_access'},
          {'label':'Undo', 'action':'manage_UndoForm'})
        )

    manage_associationsForm = PageTemplateFile(
        'www/viewRegistryAssociations',
        globals(),  __name__='manage_assocationsForm')
    
    def __init__(self, id):
        self.id = id
        self.view_types = {}

    # MANIPULATORS
    def register(self, view_type, meta_type, view_id):
        """Register a view id with the registry. Can also be used
        to change what view_id is registered.
        """
        self.view_types.setdefault(view_type, {})[meta_type] = view_id
        self.view_types = self.view_types

    def unregister(self, view_type, meta_type):
        """Unregister view_type, meta_type
        """
        del self.view_types[view_type][meta_type]
        self.view_types = self.view_types
        
    # ACCESSORS
    def get_view_types(self):
        """Get all view types, sorted.
        """
        result = self.view_types.keys()
        result.sort()
        return result

    def get_meta_types(self, view_type):
        """Get meta_types registered for view_type, sorted.
        """
        meta_types = self.view_types.get(view_type, {})
        result = meta_types.keys()
        result.sort()
        return result

    def get_view_id(self, view_type, meta_type):
        """Get view id used for view_type/meta_type combination.
        """
        return self.view_types[view_type][meta_type]

    def render_preview(self, view_type, obj):
        """Call render method for preview.
        """
        return getattr(self,
                       self.view_types[view_type][obj.meta_type]).__of__(obj).render(version=self.get_previewable())
    
    def render_view(self, view_type, obj):
        """Call render method in view.
        """
        return getattr(self,
                       self.view_types[view_type][obj.meta_type]).__of__(obj).render(version=self.get_viewable())

    
    def wrap(self, view_type, obj):
        """Wrap object in view (wrapping skin)
        """
        return getattr(self,
                       self.view_types[view_type][obj.meta_type]).__of__(obj)
    
        #return obj.__of__(getattr(
        #    self, self.view_types[view_type][obj.meta_type]))
    
Globals.InitializeClass(ViewRegistry)

manage_addViewRegistryForm = PageTemplateFile(
    "www/viewRegistryAdd", globals(),
    __name__='manage_addViewRegistryForm')

def manage_addViewRegistry(self, id, REQUEST=None):
    """Add a ViewRegistry."""
    object = ViewRegistry(id)
    self._setObject(id, object)

    add_and_edit(self, id, REQUEST)
    return ''

class ViewAttribute(Acquisition.Implicit):
    def __init__(self, view_type):
        self._view_type = view_type
            
    def __getitem__(self, name):
        """
        """    
        return getattr(self.get_view(self._view_type, self.aq_parent), name)

