## Script (Python) "move_down"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
node = context.REQUEST.node
node.sec_update_last_author_info()
n = node
while 1:
    n = n.nextSibling
    if n is None or n.nodeType == node.ELEMENT_NODE:
        break

if n is None:
    return

parent = node.parentNode
#parent.removeChild(node)
parent.insertBefore(node, n.nextSibling)
context.service_editor.setNodeWidget(node,
   context.get_widget_path()[:-1] + ('mode_done',))
return context.redirect()
