from __future__ import nested_scopes

import string
import re

# zope imports
import zLOG

# silva imports
from Products.Silva.interfaces import IUpgrader, IContainer
from Products.Silva import upgrade

#-----------------------------------------------------------------------------
# 0.9.2 to 0.9.3
#-----------------------------------------------------------------------------

class MovedViewRegistry:
    """handle view registry beeing moved out of the core"""

    __implements__ = IUpgrader

    def upgrade(self, root):
        svr = root.service_view_registry
        root._delObject('service_view_registry')
        root.manage_addProduct['SilvaViews'].manage_addMultiViewRegistry(
            'service_view_registry')
        zLOG.LOG('Silva', zLOG.WARNING,
            'service_view_registry had to be recreated.'
            "Be sure to 'refresh all' your extensions")
        return root
            

class MovedDocument:
    """handle moved silva document

        Silva Document was moved from core to a seperate package. This upgrader
        removes the objects in the silva root which were required by the
        core Silva Document.
    """

    __implements__ = IUpgrader

    def upgrade(self, root):
        root.manage_delObjects(['service_widgets', 'service_editor',
            'service_editorsupport',
            # xml widgets ahead
            'service_doc_editor', 'service_doc_previewer',
            'service_doc_viewer', 'service_field_editor',
            'service_field_viewer', 'service_nlist_editor',
            'service_nlist_previewer', 'service_nlist_viewer',
            'service_sub_editor', 'service_sub_previewer',
            'service_sub_viewer', 'service_table_editor',
            'service_table_viewer'])
        return root

upgrade.registry.registerUpgrader(MovedDocument(), '0.9.3', 'Silva Root')

            
            
class UpgradeAccessRestriction:
    """upgrade access restrction

        access restriction by ip address was a proof of concept and has been
        replaced by IP groups.

        This upgrade does:

            XXX

    """

    __implements__ = IUpgrader

    ACCESS_RESTRICTION_PROPERTY = 'access_restriction'

    # match any quote _not_ preceeded by a backslash
    re_quote_split = re.compile(r'(?<![^\\]\\)"', re.M)

    # match any escapes of quotes (e.g. \\ or \" )
    re_drop_escape = re.compile(r'\\(\\|")')


    def upgrade(self, obj):
        if not hasattr(obj.aq_base, '_properties'):
            # if it is not a property manager it hardly can have access 
            # restrictions
            return obj
        if not obj.hasProperty(self.ACCESS_RESTRICTION_PROPERTY):
            # if it doesn't have the property nothing needs to be done
            return obj
        ar = self.parseAccessRestriction(obj).get('allowed_ip_addresses')
        at_text = getattr(obj, self.ACCESS_RESTRICTION_PROPERTY, '')
        log_text = []
        if ar:
            ar = [ s.upper() for s in ar ]
            if 'NONE' in ar:
                self._none_allowed(obj, ar)
            elif 'ALL' in ar:
                self._all_allowed(obj, ar)
            else:
                self._restrict(obj, ar)
        try:
            obj._delProperty(self.ACCESS_RESTRICTION_PROPERTY)
        except ValueError:
            pass
        return obj
        
    def _all_allowed(self, obj, ar):
        zLOG.LOG('Silva', zLOG.INFO, "Access restriction removed",
            "The access restriction of the object located at %s "
            "has been removed as it allowed ALL addresses access." % (
                obj.absolute_url(), ))
                
    def _none_allowed(self, obj, ar):
        if not obj.sec_is_closed_to_public():
            obj.sec_close_to_public()
            zLOG.LOG('Silva', 'Access restriction removed', 
                "The access restriction of the object located at %s "
                "has been removed. The object's 'access restriction by role' "
                "was set to 'viewer' as the access restriction did not allow "
                "any ip addresses access." % obj.absolute_url())

    def _restrict(self, obj, ar):
        if not obj.sec_is_closed_to_public():
            obj.sec_close_to_public()
        ipg = self._createIPGroup(obj)
        for ip in ar:
            ipg.addIPRange(ip)
        self._assignRoleToGroup(obj, 'Viewer', ipg.getId())
        zLOG.LOG('Silva', zLOG.INFO, "Created IP Group %s" % ipg.getId(),
            "The ip based access restriction of the object located at %s"
            "was replaced by the newly created IP Group at %s." % (
                obj.absolute_url(), ipg.absolute_url()))
        
    def _createIPGroup(self, context):
        if not IContainer.isImplementedBy(context):
            context = context.aq_parent
        assert IContainer.isImplementedBy(context)
        id = 'access_restriction_upgrade_group'
        id_template = id + '_%i'
        counter = 0
        while 1:
            if counter:
                id = id_template % counter
            try:
                context.manage_addProduct['Silva'].manage_addIPGroup(id,
                    'Automatically created IP Group', id)
            except ValueError:
                counter += 1
            except AttributeError:
                self._createGroupsService(context)
            else:
                break
        return context._getOb(id)

    def _assignRoleToGroup(self, obj, role, group_name):
        mapping = obj.sec_get_or_create_groupsmapping()
        mapping.assignRolesToGroup(group_name, [role])

    def _createGroupsService(self, context):
        try:
            groups = context.get_root().manage_addProduct['Groups']
        except AttributeError:
            raise AttributeError, "The Groups product is not installed. "\
                "Upgrading  your ip based access restrictions requires "\
                "IP Groups and a service_groups in your Silva root."
        zLOG.LOG('Silva', zLOG.INFO, 'Upgrade added service_groups',
            'service_groups added to Silva root located at %s\n' % (
                context.get_root().absolute_url(), ))
        groups.manage_addGroupsService('service_groups', '')

    ### ACCCESS RESTRICTION PARSER
    ### formerly found in helpers.py

    # This code is based on Clemens Klein-Robbenhaar's "CommentParser.py" 
    # Marc Petitmermet's and Wolfgang Korosec's code.
    #
    def parseAccessRestriction(self, obj):
        raw_string = ''
        raw_string = getattr(obj.aq_base, self.ACCESS_RESTRICTION_PROPERTY, '')
        if not raw_string:
            return {}
        return self._parse_raw(raw_string)

    #stupid record
    class State:
        pass

    def _parse_raw(self, raw_string):
        props = {}
        state = self.State()
        # first split due to quotes
        quoted = self.re_quote_split.split(raw_string)
        in_quote = None
        state.read_props = None
        for item in quoted:
            if in_quote:
                self._parse_quote(item, state, props)
            else:
                self._parse_unquote(item, state, props)
            in_quote = not in_quote
        return props


    def _parse_unquote(self, something, state, props):
        
        if not state.read_props:
            try:
                name, something = map (string.strip, something.split(':',1) )
            except ValueError:
                # no name: quit.
                return
            state.name = name
            props[name] = []
            state.plist = props[name]
            state.read_props = 1

        separate = something.split(';',1)
        if len(separate) > 1:
            something, rest = map (string.strip, separate)
        else:
            rest=None

        for p in map (string.strip, something.split(',') ):
            if p:
                state.plist.append(p)

        if rest is not None:
            state.read_props=None
            self._parse_unquote(rest, state, props)


    def _parse_quote(self, something, state, props):
        """ parse everything enclosed in quotes.
        this is an easy one: just remove the escapes
        """
        if not state.read_props:
            raise ValueError, "not inside a property definition: <<%s>>" % something

        something = self.re_drop_escape.sub(lambda match: match.group(1), something )
        state.plist.append(something)


def initialize():
    upgrade.registry.registerFunction(upgrade.check_reserved_ids, '0.9.3',
        upgrade.AnyMetaType)
    upgrade.registry.registerUpgrader(MovedViewRegistry(), '0.9.3',
        'Silva Root')
    upgrade.registry.registerUpgrader(UpgradeAccessRestriction(), '0.9.3',
        upgrade.AnyMetaType)


