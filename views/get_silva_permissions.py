## Script (Python) "get_silva_permissions"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
from AccessControl import getSecurityManager
model = context.REQUEST.model
security_manager = getSecurityManager()
result = {}
result['ReadSilvaContent'] = security_manager.checkPermission('ReadSilvaContent', model)
result['ChangeSilvaContent'] = security_manager.checkPermission('Change Silva content', model)
result['ApproveSilvaContent'] = security_manager.checkPermission('Approve Silva content', model)
result['ChangeSilvaAccess'] = security_manager.checkPermission('Change Silva access', model)
return result
