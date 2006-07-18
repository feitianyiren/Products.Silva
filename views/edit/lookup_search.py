##parameters=name=None
from Products.Silva.i18n import translate as _

request = context.REQUEST
session = request.SESSION
model = request.model
view = context

if not name:
    name = request.form.get('name', ' ')
name = unicode(name.strip(), 'UTF-8')

if name == '':
    return view.lookup_ui(
        message_type="error", 
        message=_("No search string supplied."))

if len(name) < 2:
    msg = _("Search string '${string}' is too short. Please try a longer search string.")
    msg.set_mapping({'string': name})
    return view.lookup_ui(
        message_type="error", 
        message= msg)       

results = model.sec_find_users(name)
if not results:
    msg = _("No users found for search string '${string}'.")
    msg.set_mapping({'string': name})
    return view.lookup_ui(
        message_type="feedback", 
        message= msg)

msg = _("Searched for '${string}'.")
msg.set_mapping({'string': name})
return view.lookup_ui(
    message_type="feedback", 
    message=msg,
    results=results)

