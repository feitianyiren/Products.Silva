## Script (Python) "tag"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##

node = context.REQUEST.node
image = context.content()

if not image:
    return '<div class="error">[image reference is broken]</div>'

alignment = node.output_convert_editable(node.getAttribute('alignment'))
link = node.output_convert_editable(node.getAttribute('link'))

tag = image.image.tag(css_class=alignment)
if link:
    tag = '<a href="%s">%s</a>' % (link, tag)

if alignment.startswith('image-'):
    # I don't want to do this... Oh well, long live CSS...
    tag = '<div class="%s">%s</div>' % (
        alignment, image.image.tag(css_class=alignment))  

return tag
