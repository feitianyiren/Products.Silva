from datetime import datetime

from five import grok
from zope.component import getUtility

from AccessControl import getSecurityManager

from silva.core import interfaces
from silva.core.interfaces import events
from Products.Silva import mangle


def format_date(date):
    return mangle.DateTime(date).toStr()

def send_message_to_editors(target, from_userid, subject, text,
        message_service):
    message_service = message_service or getUtility(interfaces.IMessageService)
    # find out some information about the object and add it to the
    # message
    text = "Object: %s\n%s/edit/tab_preview\n%s" % (
        target.get_title_editable(),
        target.absolute_url(), text)
    # XXX this may not get the right people, but what does?
    for userid in target.sec_get_nearest_of_role('ChiefEditor'):
        if userid==from_userid:
            continue
        message_service.send_message(
            from_userid, userid, subject, text)

def send_message(target, from_userid, to_userid, subject, text,
        message_service=None):
    message_service = message_service or getUtility(interfaces.IMessageService)
    if from_userid==to_userid:
        return
    # find out some information about the object and add it to the
    # message
    text = "Object: %s\n%s/edit/tab_preview\n%s" % (
        target.get_title_editable(),
        target.absolute_url(), text)
    message_service.send_message(from_userid, to_userid, subject, text)

@grok.subscribe(interfaces.IVersionedContent, events.IContentApprovedEvent)
def send_messages_approved(content, event):
    # send messages
    info = event.info
    manager = interfaces.IVersionManager(content)

    if info.requester is None:
        return # no requester found, so don't send messages

    now = datetime.now()
    publication_datetime = manager.get_publication_datetime()
    expiration_datetime = manager.get_expiration_datetime()

    if publication_datetime > now:
        publication_date_str = 'The version will be published at %s\n' % \
                              format_date(publication_datetime)
    else:
        publication_date_str="The version has been published right now.\n"
    if expiration_datetime is None:
        expiration_date_str=''
    else:
        expiration_date_str = 'The version will expire at %s\n' % \
                              format_date(expiration_datetime)
    editor = getSecurityManager().getUser().getId()
    text = u"\nVersion was approved for publication by %s.\n%s%s" % \
            (editor, publication_date_str, expiration_date_str)

    message_service = getUtility(interfaces.IMessageService)
    message_service.send_message(editor, info.requester,
                       "Version approved", text)

@grok.subscribe(interfaces.IVersionedContent, events.IContentUnApprovedEvent)
def send_messages_unapproved(content, event):
    # send messages to editor
    author = getSecurityManager().getUser().getId()
    text = u"\nVersion was unapproved by %s." % author
    message_service = getUtility(interfaces.IMessageService)
    send_message_to_editors(author, 'Unapproved', text,
        message_service=message_service)
    if event.info.requester is not None:
        send_message(author, event.info.requester, 'Unapproved', text,
            message_service=message_service)

@grok.subscribe(interfaces.IVersionedContent,
                events.IContentRequestApprovalEvent)
def send_messages_request_approval(content, event):
    last_author = content.sec_get_last_author_info()
    info = event.info
    manager = interfaces.IVersionManager(content)
    publication_datetime = manager.get_publication_datetime()
    expiration_datetime = manager.get_expiration_datetime()
    message = info.request_messages[-1]

    if publication_datetime is None:
        publication_date_str=''
    else:
        publication_date_str = \
                 'The version has a proposed publication date of %s\n' % \
                 format_date(publication_datetime)
    if expiration_datetime is None:
        expiration_date_str=''
    else:
        expiration_date_str = \
           'The version has a proposed expiration date of %s\n' % \
           format_date(expiration_datetime)
    # send messages
    text = u"\nApproval was requested by %s.\n%s%s\nMessage:\n%s" % \
            (info.requester,
             publication_date_str, expiration_date_str, message)
    message_service = getUtility(interfaces.IMessageService)
    send_message_to_editors(info.requester,
                            'Approval requested', text,
                            message_service=message_service)
    # XXX inform user, too (?)
    send_message(info.requester, last_author.userid(),
                 'Approval requested', text,
                 message_service=message_service)

@grok.subscribe(interfaces.IVersionedContent,
                events.IContentApprovalRequestCanceledEvent)
def send_messages_content_approval_request_canceled(content, event):
    info = event.info
    original_requester = event.original_requester
    message = info.request_messages[-1]

    # send messages
    text = u"\nRequest for approval was withdrawn by %s.\nMessage:\n%s" \
           % (info.requester, message)
    message_service = getUtility(interfaces.IMessageService)
    send_message_to_editors(content, info.requester,
                            'Approval withdrawn by author', text,
                            message_service=message_service)
    send_message(content, info.requester, original_requester,
                       'Approval withdrawn by author', text,
                       message_service=message_service)

@grok.subscribe(interfaces.IVersionedContent,
                events.IContentApprovalRequestRefusedEvent)
def send_messages_content_approval_request_refused(content, event):
    message = event.info.request_messages[-1]
    text = u"Request for approval was rejected by %s.\nMessage:\n%s" \
           % (event.info.requester, message)
    send_message(event.info.requester, event.original_requester,
        "Approval rejected by editor", text)


