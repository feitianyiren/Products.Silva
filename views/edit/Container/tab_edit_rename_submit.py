## Script (Python) "tab_edit_rename_submit"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
import random

form = context.REQUEST.form
model = context.REQUEST.model
items = []

messages = []
message_type = None

# make a list of items, tuples with old and new data (oldid, newid, newtitle)
for key in form.keys():
    if key[:2] == "id":
        oldid = key[3:]
        try:
            newid = form[key].encode('ascii')
        except:
            messages.append(u'&#xab;%s&#xbb; could not be renamed to %s (invalid id)' % (oldid, unicode(form[key], 'UTF-8')))
            message_type = 'error'
        else:
            newtitle = form["title_" + oldid]
            items.append((oldid, newid, newtitle))

# remove the items that are not renamed, change only the title
to_rename = []
for item in items:
    if item[0] == item[1]:
            obj = getattr(model, item[0])
            obj.set_title(model.input_convert(item[2]))
            message_type = 'feedback'
            messages.append('&#xab;%s&#xbb; renamed successfully' % item[0])
    else:
        to_rename.append(item)

items = to_rename

# now walk through the list, renaming every item in the list if possible. repeat this procedure as long as names can be replaced,
# for it is possible a name that was used in the first round became available in the next
not_renamed = []
while 1:
    objects_changed = 0
    for item in items:
        if not model.is_id_valid(item[1]):
            messages.append('&#xab;%s&#xbb; could not be renamed to %s (invalid id)' % (item[0], item[1]))
            message_type = 'error'
        elif not item[1] in model.objectIds():
            # The item can be renamed without any problems, so do that
            if item[0] != 'index':
                obj = getattr(model, item[0])
                obj.set_title(model.input_convert(item[2]))
                if not model.action_rename(item[0], item[1]):
                    message_type = 'error'
                    messages.append('&#xab;%s&#xbb; could not be renamed' % item[0])
                else:
                    if message_type is None:
                        message_type = 'feedback'
                    messages.append('&#xab;%s&#xbb; renamed successfully' % item[0])
            else:
                # for the index, if the title is set before the id is changed, the title of the container is changed instead...
                obj = getattr(model, item[0])
                if not model.action_rename(item[0], item[1]):
                    message_type = 'error'
                    messages.append('&#xab;%s&#xbb; could not be renamed' % item[0])
                else:
                    if message_type is None:
                        message_type = 'feedback'
                    messages.append('&#xab;%s&#xbb; renamed successfully' % item[0])
                    obj = getattr(model, item[1])
                    obj.set_title(model.input_convert(item[2]))
            objects_changed = 1
        else:
            not_renamed.append(item)
    if objects_changed == 0:
        # nothing changed, so we can quit trying, there's no chance any names became free this round
        break
    items = not_renamed
    not_renamed = []

# now we're left with either some conflicting names or some illegal ones...
# create a temporary name for all the objects that cannot be renamed directly, then first rename them to their temporary name,
# then try to rename them to their new name. If that still doesn't work, prefix the names with 'renamed ' until the name is unique
# so the name "foo" would become "renamed_foo" if another "foo" exists, and "renamed_renamed_foo" if there is already a "renamed_foo"...
# First create some unique names
unique_names = []
for i in range(len(not_renamed)):
    unique_name = ""
    while not unique_name or unique_name in model.objectIds() or unique_name in unique_names:
        unique_name += string.lowercase[random.randrange(26)]
    # this reformats the items in not_renamed to ((oldid, newid, newtitle), unique_name)
    unique_names.append(unique_name)
    not_renamed[i] = (not_renamed[i], unique_name)

renamed_now = []
# now change the ids to unique ones
for item in not_renamed:
    if not model.action_rename(item[0][0], item[1]):
        # this item can not be renamed, stop processing it
        message_type = 'error'
        messages.append('&#xab;%s&#xab; could not be renamed' % item[0][0])
    else:
        renamed_now.append(item)

# and the unique ones to the new ones
for item in renamed_now:
    oldid = item[0][0]
    newid = item[0][1]
    tmpid = item[1]
    # if the id still exists, change it until it becomes unique (by prefixing 'renamed ')
    while newid in model.objectIds():
        newid = "renamed_" + newid
    obj = getattr(model, tmpid)
    if oldid != 'index':
        obj.set_title(model.input_convert(item[0][2]))
    if not model.action_rename(tmpid, newid):
        message_type = 'error'
        messages.append('&#xab;%s&#xab; could not be renamed' % oldid)
    else:
        if message_type is None:
            message_type = 'feedback'
        messages.append('&#xab;%s&#xbb; renamed successfully' % oldid)
    if oldid == 'index':
        # set title of new obj so the title of container does not get affected
        obj = getattr(model, newid)
        obj.set_title(model.input_convert(item[0][2]))

# send the user back to the list
return context.tab_edit(message_type=message_type, message=', '.join(messages))
