from Products.Silva import subscriptionerrors
from Products.Silva.i18n import translate as _

request = context.REQUEST
service = context.service_subscriptions

content = context.restrictedTraverse(request['path'], None)
if content is None:
    return context.subscriptions(
        message=_('Path does not lead to a content object'))

try:
    service.requestCancellation(content, request['emailaddress'])
except subscriptionerrors.EmailaddressError, e:
    # We just pretend to have sent email in order not to expose
    # any information on the validity of the emailaddress
    pass
except subscriptionerrors.SubscriptionError, e:
    return str(e)

return context.subscriptions(
    message=_('Confirmation request for cancellation has been emailed'))
