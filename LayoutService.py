
# Copyright (c) 2002 Infrae. All rights reserved.
# See also LICENSE.txt
# $Revision: 1.3 $
# Zope
from OFS import SimpleItem
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from DateTime import DateTime
# Silva
from helpers import add_and_edit
import SilvaPermissions
from LayoutRegistry import layoutRegistry
import install
import whrandom
import copy

class LayoutService(SimpleItem.SimpleItem):
    meta_type = 'Silva Layout Service'

    security = ClassSecurityInfo()
    
    manage_options = (
        {'label':'Edit', 'action':'manage_editForm'},
        ) + SimpleItem.SimpleItem.manage_options

    security.declareProtected('View management screens', 'manage_editForm')
    manage_editForm = PageTemplateFile(
        'www/layoutServiceEdit', globals(),  __name__='manage_editForm')

    security.declareProtected('View management screens', 'manage_main')
    manage_main = manage_editForm

    def __init__(self, id, title):
        self.id = id
        self.title = title
        self._refresh_datetime = DateTime()
        self._used_layouts = {}
        
    # MANIPULATORS

    security.declareProtected('View management screens', 'install')
    def install(self, name):
        """Install layout
        """
        layoutRegistry.install(self.get_root(), name)
        return self.manage_main(manage_tabs_message='%s installed' % name)

    security.declareProtected('View management screens', 'uninstall')
    def uninstall(self, name):
        """Uninstall extension
        """
        layoutRegistry.uninstall(self.get_root(), name)
        return self.manage_main(manage_tabs_message='%s uninstalled' % name)

    security.declareProtected('View management screens', 'refresh')

    def refresh(self, name):
        """Refresh (uninstall/install) extension.
        """
        self.uninstall(name)
        self.install(name)
        self._refresh_datetime = DateTime()
        return self.manage_main(manage_tabs_message='%s refreshed' % name)

    security.declareProtected('View management screens', 'refresh_all')
    def refresh_all(self):
        """Refreshes all extensions
        """
        for name in self.get_installed_names():
            self.refresh(name)
        return self.manage_main(manage_tabs_message='All layouts have been refreshed')

    # ACCESSORS

    security.declareProtected('View management screens', 'get_names')
    def get_names(self):
        """Return registered extension names
        """
        list = layoutRegistry.get_names()
        list.sort()
        return list

    def get_installed_names(self):
        """Return installed extension names
        """
        return [name for name in self.get_names()
                if self.is_installed(name)]
    
    NOLAYOUT = 'No layout, select one !'

    def get_installed_for_select(self):
        result = [(self.NOLAYOUT, '')]
        for name in self.get_names():
            layout = layoutRegistry.get_layout(name)
            result.append((layout.description, name))
        return result

    security.declareProtected('View management screens', 'get_description')
    def get_description(self, name):
        """Return description of extension
        """
        return layoutRegistry.get_description(name)

    security.declareProtected('View management screens', 'is_installed')
    def is_installed(self, name):
        """Is extension installed?
        """
        return layoutRegistry.is_installed(self.get_root(), name)

    security.declareProtected('View management screens',
                              'get_refresh_datetime')
    def get_refresh_datetime(self):
        """Get datetime of last refresh.
        """
        return self._refresh_datetime

    # USED LAYOUTS

    def setup_layout(self, layout, target):
        layoutRegistry.setup_layout(self.get_root(), layout, target)
        if not target.get_layout_key():
            target.set_layout_key(self._get_unique_layout_key())
        newUsedLayout = usedLayout(layout)
        newUsedLayout.set_items(layoutRegistry.layout_items(self.get_root(), layout))
        self._used_layouts[target.get_layout_key()] = newUsedLayout
        self._p_changed = 1

    def clone_layout(self, target):
        old_key = target.get_layout_key()
        if old_key:
            target.set_layout_key(self._get_unique_layout_key())
            newUsedLayout = copy.copy(self._used_layouts[old_key])
            self._used_layouts[target.get_layout_key()] = newUsedLayout
        self._p_changed = 1

    def remove_layout(self, target):
        layout_items = [id for id in self.layout_items(target) if hasattr(target.aq_base, id)]
        target.manage_delObjects(layout_items)

        del self._used_layouts[target.get_layout_key()]
        self._p_changed = 1

        target.set_layout_key(None)
        
    def _get_unique_layout_key(self):
        unique = str(whrandom.random())
        while self._used_layouts.has_key(unique):
            unique = str(whrandom.random())
        return unique

    def has_layout(self, publication):
        return self._used_layouts.has_key(publication.get_layout_key())

    def layout_items(self, publication):
        usedLayout = self._used_layouts.get(publication.get_layout_key(), None)
        if usedLayout is None:
            return []
        else:
            return usedLayout.get_items()

class usedLayout:
    def __init__(self, name):
        self.name = name
        self.items = []

    def set_items(self, items):
        self.items = items

    def get_items(self):
        return self.items
    
InitializeClass(LayoutService)

manage_addLayoutServiceForm = PageTemplateFile(
    "www/layoutServiceAdd", globals(), __name__='manage_addLayoutServiceForm')

def manage_addLayoutService(self, id, title='', REQUEST=None):
    """Add extension service."""
    object = LayoutService(id, title)    
    self._setObject(id, object)
    object = getattr(self, id)
    add_and_edit(self, id, REQUEST)
    return ''
