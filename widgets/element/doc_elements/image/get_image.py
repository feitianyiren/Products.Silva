## Script (Python) "get_image"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=image_path
##title=
##
try:
    image = context.restrictedTraverse(image_path)
except (KeyError, AttributeError, ValueError, IndexError):
    # image reference is broken (i.e. renamed)
    image = None
if getattr(image, 'meta_type', None) != 'Silva Image':
    image = None
return image

