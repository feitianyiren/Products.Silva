## Script (Python) "redirect"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
context.REQUEST.model
view = context
content_url = model.content_url() + '/edit/tab_edit'

if context.REQUEST['HTTP_USER_AGENT'].startswith('Mozilla/4.77'):
    return '<html><head><META HTTP-EQUIV="refresh" CONTENT="0; URL=%s"></head><body bgcolor="#FFFFFF"></body></html>' % content_url  
else:
    return context.REQUEST.RESPONSE.redirect(content_url)
