## Script (Python) "access_remove_user"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=userids=None
##title=
##
view = context
model = context.REQUEST.model

if not userids:
    return view.tab_access(
        message_type="error", message="No user(s) selected, so none removed")

for id in userids:
    model.sec_remove(id)

view.lookup_remove_from_selection(userids)

return view.tab_access(message_type="feedback", message="User(s) removed")
