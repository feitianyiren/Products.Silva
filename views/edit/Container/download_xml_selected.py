## Script (Python) "download_xml"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=with_sub_publications=0, export_last_version=0
##title=
##
view = context
request = view.REQUEST
RESPONSE = view.REQUEST.RESPONSE
model = request.model

from DateTime import DateTime

if not request.has_key('refs') or not request['refs']:
    return view.tab_status(message_type='error', message='No items were selected, so nothing is exported')

objects = []
for ref in request['refs'].split('||'):
    objects.append(model.resolve_ref(ref))

data = model.get_xml_for_objects(objects, with_sub_publications, export_last_version)

RESPONSE.setHeader('Content-Type', 'application/download')
RESPONSE.setHeader('Content-Length', len(data))
RESPONSE.setHeader('Content-Disposition',
                   'attachment;filename=%s_export_%s.slv' % (model.id, DateTime().strftime('%Y-%m-%d')))

return data
