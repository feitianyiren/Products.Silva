## Script (Python) "tab_access_revoke"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
view = context
request = context.REQUEST
model = context.REQUEST.model

revoke_roles = request.form.get('revoke_roles', None)
if revoke_roles is None:
    return view.tab_access(
        message_type="error", 
        message="No roles to revoke selected.")

def extract_users_and_roles(in_list):
    out_list = []
    for item in in_list:
        user,role = item.split('||')
        out_list.append((user,role))
    return out_list

revoked = []
for user, role in extract_users_and_roles(revoke_roles):
    model.sec_revoke(user, [role])
    revoked.append((user, role))

return view.tab_access(
    message_type="feedback", 
    message="Role(s) revoked for %s" % context.quotify_list_ext(revoked))
