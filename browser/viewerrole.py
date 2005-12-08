from Products.Silva.i18n import translate as _

from Products.Silva.adapters.security import getViewerSecurityAdapter
from Products.Silva.roleinfo import ASSIGNABLE_VIEWER_ROLES

from Products.Five import BrowserView

class ViewerRole(BrowserView):
    def getViewerRoleInfo(self):
        viewer_security = getViewerSecurityAdapter(self.context.aq_inner)

        acquired = viewer_security.isAcquired()
        selected_role = viewer_security.getMinimumRole()
        above_role = viewer_security.getMinimumRoleAbove()
        is_public = selected_role == 'Anonymous'
        
        viewer_roles = ASSIGNABLE_VIEWER_ROLES
        if not is_public and above_role != 'Anonymous':
            viewer_roles = ASSIGNABLE_VIEWER_ROLES[1:]
    
        return {
            'acquired': acquired,
            'selected_role': selected_role,
            'viewer_roles': viewer_roles,
            'is_public': is_public,
            }
    
    def submitMinimumRole(self):
        self.request.response.setHeader('Content-Type',
                                        "text/html; charset='UTF-8'")

        context = self.context.aq_inner
        
        viewer_security = getViewerSecurityAdapter(context)
    
        old_role = viewer_security.getMinimumRole()
        role = self.request['role']
        
        # we don't want to change the role if we already set it
        if old_role == role and not viewer_security.isAcquired():
            return context.edit['tab_access'](
                message_type='feedback',
                message=_("Minimum role to access has not changed"))
        
        viewer_security.setMinimumRole(role)

        msg = _("Minimum role to access is now set to ${role}")
        msg.set_mapping({'role': role})
        return context.edit['tab_access'](
            message_type='feedback',
            message= msg)

    def submitAcquiredMinimumRole(self):
        self.request.response.setHeader('Content-Type',
                                        "text/html; charset='UTF-8'")
        
        context = self.context.aq_inner
        
        viewer_security = getViewerSecurityAdapter(context)
        viewer_security.setAcquired()
        return context.edit['tab_access'](
            message_type='feedback',
            message=_('Minimum role to access is now acquired'))
