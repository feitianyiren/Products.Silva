## Script (Python) "get_link_status_text"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=ghost_version
##title=
##
status = ghost_version.get_link_status()
if status == ghost_version.LINK_OK:
  return ''
elif status == ghost_version.LINK_EMPTY:
  return 'You have to enter a path here.'
elif status == ghost_version.LINK_VOID:
  return 'The object &#xab;%s&#xbb; the ghost points to does not exist.' %  \
    ghost_version.get_haunted_url()
elif status == ghost_version.LINK_FOLDER:
  return 'The object &#xab;%s&#xbb; the ghost points to is a container.' % \
    ghost_version.get_haunted_url()
elif status == ghost_version.LINK_GHOST:
  return 'The object &#xab;%s&#xbb; the ghost points to is itself a ghost.' % \
    ghost_version.get_haunted_url()
elif status == ghost_version.LINK_NO_CONTENT:
  return 'The object &#xab;%s&#xbb; the ghost points to is not a content object.' % \
    ghost_version.get_haunted_url()
elif status == ghost_version.LINK_CONTENT:
  return 'The object &#xab;%s&#xbb; the ghost points to is a content object.' % \
    ghost_version.get_haunted_url()
elif status == ghost_version.LINK_NO_FOLDER:
  return 'The object &#xab;%s&#xbb; the ghost points to is not a container.' % \
    ghost_version.get_haunted_url()
elif status == ghost_version.LINK_CIRC:
    return 'The object &#xab;%s&#xbb; the ghost points is either the ghost ' \
        'itself or an ancestor of the ghost.' % \
        ghost_version.get_haunted_url()
return 'The ghost is in an undefined state.'


