##parameters=layout,partkey,current
from Products.Silva.i18n import translate as _
from zope.i18n import translate

request = context.REQUEST
model = request.model
view = context

model.service_sticky_content.changePlacementForStickyContent(layout, int(partkey), current)

return view.tab_sticky_content(message_type='feedback',
                               message=_('changed sticky content placement'))
