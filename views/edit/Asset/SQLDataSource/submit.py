## Script (Python) "submit"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
from Products.Formulator.Errors import ValidationError, FormValidationError

model = context.REQUEST.model
view = context

try:
    result = view.form.validate_all_to_request(context.REQUEST)
except FormValidationError, e:
    return view.tab_edit(
        message_type="error", message=context.render_form_errors(e))

changed = []
current_title = model.get_title_html()
new_title = model.input_convert(result['object_title'])
if current_title != new_title:
    model.sec_update_last_author_info()
    model.set_title(new_title)
    changed.append(('title', '%s to %s' % (
        current_title, model.get_title_html())))

new_parameters = model.parameter_string_to_dict(result['parameters'])
current_parameters = model.parameters()

# clear parameters if not in new_parameters:
curr_names = current_parameters.keys() 
new_names = new_parameters.keys()
for name in curr_names:
    if name not in new_names:
        model.unset_parameter(name)
        changed.append(('removed parameter', name))

# check param by param whether it should change:
for name in new_names:
    if name in curr_names:
        if current_parameters[name] != new_parameters[name]:
            (type, default_value, description) = new_parameters[name]
            model.set_parameter(
                name=name, type=type, default_value=default_value, 
                description=description)
            changed.append(('changed parameter', name))
    else:
        # does not exist, so add
        (type, default_value, description) = new_parameters[name]
        model.set_parameter(
            name=name, type=type, default_value=default_value, 
            description=description)
        changed.append(('added parameter', name))

curr_statement = model.statement()
new_statement = result['statement']
if curr_statement != new_statement:
    model.set_statement(new_statement)
    changed.append(('query changed', ''))

if not changed:
    return view.tab_edit(
        message_type="feedback", 
        message="Nothing changed")
else:
    return view.tab_edit(
        message_type="feedback", 
        message="Settings changed: %s" % (
            context.quotify_list_ext(changed)))
