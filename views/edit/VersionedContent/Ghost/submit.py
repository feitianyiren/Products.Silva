## Script (Python) "submit"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=content_url
##title=
##
model = context.REQUEST.model
view = context
if context.REQUEST.has_key('add_cancel'):
    return view.tab_edit()
model.sec_update_last_author_info()
model.get_editable().set_content_url(content_url)
return view.tab_edit(message_type="feedback", message="Ghost changed.")
