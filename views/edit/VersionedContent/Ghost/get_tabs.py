## Script (Python) "get_tabs"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
# define:
# name, id/None, up_id, toplink_accesskey, tab_accesskey, uplink_accesskey
tabs = [('Edit', 'tab_edit', 'tab_edit', '!', '1', '6'),
        ('Preview', 'tab_preview', 'tab_preview', '@', '2', '7'),
        ('Publish', 'tab_status', 'tab_status', '%', '3', '8'),
       ]

return tabs
