##parameters=set_name,element_name
from Products.SilvaMetadata.Exceptions import BindingError

request = context.REQUEST
model = request.model
content = model.get_viewable()

if content is None:
    return None

ms = context.service_metadata

try:
    binding = ms.getMetadata(content)
except BindingError, be:
    # No binding found..
    return None
if binding is None:
    return None

return binding.get(set_name, element_name)
