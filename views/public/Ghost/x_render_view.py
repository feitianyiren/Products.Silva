## Script (Python) "x_render_view"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
model = context.REQUEST.model
version = model.get_viewable()
result = version.render_view()
if result is None:
   return "This ghost is broken. Please inform the site administrator."
else:
   return result
