# -*- coding: utf-8 -*-
# Copyright (c) 2002-2010 Infrae. All rights reserved.
# See also LICENSE.txt

from cStringIO import StringIO
from cgi import escape
import logging
import mimetypes
import os.path
import re

# Zope 3
from five import grok
from zope.component import getMultiAdapter, getUtility
from zope.event import notify
from zope.lifecycleevent import ObjectCreatedEvent
from zope.lifecycleevent.interfaces import IObjectMovedEvent

# Zope 2
from AccessControl import ClassSecurityInfo
from App.class_init import InitializeClass

# Silva
from silva.core import conf as silvaconf
from silva.core import interfaces
from silva.core.interfaces import IMimeTypeClassifier
from silva.core.services.interfaces import IFilesService
from silva.translations import translate as _
from silva.core.views.interfaces import IContentURL

from .. import mangle, SilvaPermissions
from ..Asset import Asset
from ..MimetypeRegistry import mimetypeRegistry
from .utils import Rect, Size, Format, Point
from .utils import WHResizeSpec, PercentResizeSpec

try:
    from PIL import Image as PILImage
except ImportError:
    import Image as PILImage
havePIL = 1


logger = logging.getLogger('silva.image')


def validate_image(file):
    """Validate that file contains an image which is openable by PIL.
    """
    try:
        # Try to validate file format.
        file.seek(0)
        PILImage.open(file)
    except IOError, error:
        raise ValueError(error.args[-1].capitalize())
    # Come back at the begining..
    finally:
        file.seek(0)


def manage_addImage(context, identifier, title=None, file=None):
    """Add an Image.
    """
    if file is not None:
        validate_image(file)

    filename = None
    if hasattr(file, 'name'):
        filename = os.path.basename(file.name)
    identifier = mangle.Id(
        context, identifier or filename, file=file, interface=interfaces.IAsset)
    identifier.cook()
    if not identifier.isValid():
        raise ValueError(_(u"Invalid computed identifier."))
    identifier = str(identifier)
    if identifier in context.objectIds():
        raise ValueError(
            _(u"Duplicate id. Please provide an explicit id."))
    context._setObject(identifier, Image(identifier))
    content = context._getOb(identifier)
    if title is not None:
        content.set_title(title)
    if file is not None:
        content.set_image(file)
    notify(ObjectCreatedEvent(content))
    return content


class ImageFile(object):

    def __init__(self, image):
        if image is None:
            raise ValueError("Missing image.")
        self._fd = image.get_file_fd()
        self._changed = False
        try:
            self.image = PILImage.open(self._fd)
        except IOError, error:
            self._fd.close()
            raise ValueError(error.args[-1].capitalize())

    def save(self, save_format):
        if self._changed or save_format != self.image.format:
            if save_format == Format.JPEG and self.image.mode != 'RGB':
                self.image = self.image.convert("RGB")
            data = StringIO()
            self.image.save(data, save_format)
            data.seek(0)
            return data
        return None

    def resize(self, size):
        assert isinstance(size, Size)
        self.image = self.image.resize(
            (size.width, size.height),
            PILImage.ANTIALIAS)
        self._changed = True

    def thumbnail(self, size):
        self.image.thumbnail(
            (size.width, size.height),
            PILImage.ANTIALIAS)
        self._changed = True

    def crop(self, box):
        assert isinstance(box, Rect)
        self.image = self.image.crop(
            (box.lower_edge.x,
             box.lower_edge.y,
             box.higher_edge.x,
             box.higher_edge.y))
        self._changed = True

    def get_box(self):
        box = self.image.getbbox()
        if box is None:
            return None
        x1, y1, x2, y2 = box
        return Rect.from_points(Point(x1, y1), Point(x2, y2))

    def get_size(self):
        return Size(*self.image.size)

    def get_format(self):
        return self.image.format

    def __enter__(self):
        return self

    def __exit__(self, t, v, tb):
        self._fd.close()


class Transformation(object):

    def validate(self):
        """Raise ValueError on failure.
        """
        pass

    def __call__(self, image):
        """Apply transformation on image and return new image
        if modified else False.
        """
        return False


class Crop(Transformation):

    def __init__(self, box):
        self.box = box

    def validate(self, image):
        box = image.get_box()
        if box.size < self.box.size:
            raise ValueError(
                _(u"'${crop}' defines an impossible cropping for the current image",
                  mapping={'crop': str(self.box)}))

    def __call__(self, image):
        image.crop(self.box)


class Resize(Transformation):

    def __init__(self, spec):
        self.spec = spec

    def __call__(self, image):
        current_size = image.get_size()
        expected_size = self.spec.get_size(image)
        if current_size != expected_size:
            image.resize(expected_size)


class ThumbnailResize(Transformation):

    def __init__(self, size):
        self.size = size

    def __call__(self, image):
        image.thumbnail(self.size)



class Transformer(object):

    def __init__(self, *transformations):
        self.transformations = list(transformations)

    def append(self, transform):
        self.transformations.append(transform)

    def transform(self, stream, output_format):
        with ImageFile(stream) as image:
            for transformation in self.transformations:
                transformation(image)
            return image.save(output_format)



class Image(Asset):
    __doc__ = _("""Web graphics (gif, jpg, png) can be uploaded and inserted in
       documents, or used as viewable assets.
    """)
    security = ClassSecurityInfo()

    meta_type = "Silva Image"

    grok.implements(interfaces.IImage)

    re_WidthXHeight = re.compile(r'^([0-9]+|\*)[Xx]([0-9\*]+|\*)$')
    re_percentage = re.compile(r'^([0-9\.]+)\%$')
    re_box = re.compile(r'^([0-9]+)[Xx]([0-9]+)-([0-9]+)[Xx]([0-9]+)')

    thumbnail_size = Size(120, 120)

    image = None
    hires_image = None
    thumbnail_image = None
    web_scale = '100%'
    web_crop = ''
    web_format = Format.JPEG
    web_formats = (Format.JPEG, Format.GIF, Format.PNG)

    _web2ct = {
        Format.JPEG: 'image/jpeg',
        Format.GIF: 'image/gif',
        Format.PNG: 'image/png',
    }

    silvaconf.priority(-3)
    silvaconf.icon('www/silvaimage.gif')
    silvaconf.factory('manage_addImage')

    security.declareProtected(
        SilvaPermissions.ChangeSilvaContent, 'set_web_presentation_properties')
    def set_web_presentation_properties(self, web_format, web_scale, web_crop):
        """Sets format and scaling for web presentation.

        web_format (str): either JPEG or PNG (or whatever other format
        makes sense, must be recognised by PIL).
        web_scale (str): WidthXHeight or nn.n%.
        web_crop (str): X1xY1-X2xY2, crop-box or empty for no cropping.

        Raises ValueError if web_scale cannot be parsed.

        Automaticaly updates cached web presentation image.
        """
        update_cache = False
        if self.hires_image is None:
            update_cache = True
            self.hires_image = self.image
            self.image = None
        if web_format != 'unknown':
            if self.web_format != web_format and \
                    web_format in self.web_formats:
                self.web_format = web_format
                update_cache = True
        # check if web_scale can be parsed:
        self.get_canonical_web_scale(web_scale)
        if self.web_scale != web_scale:
            update_cache = True
            self.web_scale = web_scale
        # check if web_crop can be parsed:
        self.get_crop_box(web_crop)
        if self.web_crop != web_crop:
            update_cache = True
            # if web_crop is None it should be replaced by an empty string
            self.web_crop = web_crop and web_crop or ''
        if self.hires_image is not None and update_cache:
            self._create_derived_images()

    security.declareProtected(
        SilvaPermissions.ChangeSilvaContent, 'set_image')
    def set_image(self, file):
        """Set the image object.
        """
        validate_image(file)
        self._image_factory('hires_image', file)
        # Image change, reset scale, crop box: they can be invalid for
        # this new image.
        format = self.get_format()
        if format in self.web_formats:
            self.web_format = format
        self.web_scale = '100%'
        self.web_crop = ''
        self._create_derived_images()
        # XXX Should be on event
        self.update_quota()

    security.declareProtected(SilvaPermissions.View, 'get_image')
    def get_image(self, hires=True, webformat=False):
        """Return image data.
        """
        if hires and not webformat:
            image = self.hires_image
        elif not hires and webformat:
            image = self.image
        elif hires and webformat:
            with ImageFile(self.hires_image) as image:
                data = image.save(self.web_format)
            if data is not None:
                return data.getvalue()
            image = self.hires_image
        elif not hires and not webformat:
            raise ValueError(_(u"Low resolution image in original format is "
                               u"not supported"))
        return image.get_file()

    security.declareProtected(SilvaPermissions.View, 'get_canonical_web_scale')
    def get_canonical_web_scale(self, scale=None):
        """returns (width, height) of web image"""
        if scale is None:
            scale = self.web_scale
        m = self.re_WidthXHeight.match(scale)
        if m is None:
            m = self.re_percentage.match(scale)
            if m is None:
                msg = _("'${scale}' is not a valid scale identifier. "
                        "Probably a percent symbol is missing.",
                        mapping={'scale': scale})
                raise ValueError(msg)
            cropbox = Rect.parse(self.web_crop)
            if cropbox:
                width, height = cropbox.size
            else:
                width, height = self.get_dimensions()
            percentage = float(m.group(1))/100.0
            width = int(width * percentage)
            height = int(height * percentage)
        else:
            img_w, img_h = self.get_dimensions()
            width = m.group(1)
            height = m.group(2)
            if width == height == '*':
                msg = _("'${scale} is not a valid scale identifier. "
                        "At least one number is required.",
                        mapping={'scale': scale})
                raise ValueError(msg)
            if width == '*':
                height = int(height)
                width = img_w * height / img_h
            elif height == '*':
                width = int(width)
                height = img_h * width / img_w
            else:
                width = int(width)
        return width, height

    security.declareProtected(SilvaPermissions.View, 'get_crop_box')
    def get_crop_box(self, crop=None):
        """return crop box"""
        crop = crop or self.web_crop
        if crop is None or crop.strip() == '':
            return None
        rect = Rect.parse(crop)
        if rect is None:
            msg = _("'${crop} is not a valid crop identifier",
                    mapping={'crop': crop})
            raise ValueError(msg)
        with ImageFile(self.hires_image) as image:
            Crop(rect).validate(image)
        return (rect.lower_edge.x, rect.lower_edge.y,
                rect.higher_edge.x, rect.higher_edge.y)

    security.declareProtected(SilvaPermissions.View, 'get_dimensions')
    def get_dimensions(self, thumbnail=False, hires=False):
        """Returns width, heigt of (hi res) image.

        Raises ValueError if there is no way of determining the dimenstions,
        Return 0, 0 if there is no image,
        Returns width, height otherwise.
        """
        data = None
        if thumbnail:
            data = self.thumbnail_image
        elif hires:
            data = self.hires_image
        else:
            data = self.image

        if data is None:
            return Size(0, 0)
        try:
            with ImageFile(data) as image:
                return image.get_size()
        except (ValueError, TypeError):
            return Size(0, 0)

    security.declareProtected(SilvaPermissions.View, 'tag')
    def tag(self, hires=False, thumbnail=False,
            request=None, preview=False, **extra_attributes):
        """ return xhtml tag

        Since 'class' is a Python reserved word, it cannot be passed in
        directly in keyword arguments which is a problem if you are
        trying to use 'tag()' to include a CSS class. The tag() method
        will accept a 'css_class' argument that will be converted to
        'class' in the output tag to work around this.
        """
        url = self.url(request=request,
                       preview=preview,
                       hires=hires,
                       thumbnail=thumbnail)

        title = self.get_title_or_id()
        width, height = self.get_dimensions(thumbnail=thumbnail, hires=hires)
        if extra_attributes.has_key('css_class'):
            extra_attributes['class'] = extra_attributes['css_class']
            del extra_attributes['css_class']

        extra_html_attributes = [
            u'{name}="{value}"'.format(name=escape(name, 1),
                                      value=escape(value, 1))
            for name, value in extra_attributes.iteritems()]

        return u'<img src="{src}" width="{width}" height="{height}" ' \
               u'alt="{alt}" {extra_attributes} />'.format(
                    src=url,
                    width=str(width),
                    height=str(height),
                    alt=escape(title, 1),
                    extra_attributes=u" ".join(extra_html_attributes))

    security.declareProtected(SilvaPermissions.View, 'url')
    def url(self, hires=False, thumbnail=False, request=None, preview=False):
        "return url of image"
        if request is None:
            request = self.REQUEST
        url = getMultiAdapter((self, request), IContentURL).url(preview=preview)
        if hires:
            url += '?hires'
        elif thumbnail:
            url += '?thumbnail'
        return url

    security.declareProtected(SilvaPermissions.View, 'get_web_format')
    def get_web_format(self):
        """Return file format of web presentation image
        """
        try:
            with ImageFile(self.image) as image:
                return image.get_format()
        except (ValueError, TypeError):
            return 'unknown'

    security.declareProtected(SilvaPermissions.View, 'get_web_scale')
    def get_web_scale(self):
        """Return scale percentage / WxH of web presentation image
        """
        return str(self.web_scale)

    security.declareProtected(SilvaPermissions.View, 'get_web_crop')
    def get_web_crop(self):
        """Return crop identifier
        """
        return str(self.web_crop)

    security.declareProtected(SilvaPermissions.View, 'get_orientation')
    def get_orientation(self):
        """Returns translated Image orientation (string).
        """
        width, height = self.get_dimensions()
        if width == height:
            return _("square")
        elif width > height:
            return _("landscape")
        return _("portrait")

    security.declareProtected(
        SilvaPermissions.ChangeSilvaContent, 'get_file_system_path')
    def get_file_system_path(self):
        """return path on filesystem for containing image"""
        return self.hires_image.get_file_system_path()

    security.declareProtected(SilvaPermissions.View, 'get_format')
    def get_format(self):
        """Returns image format.
        """
        try:
            with ImageFile(self.hires_image) as image:
                return image.get_format()
        except (ValueError, TypeError):
            return 'unknown'

    security.declareProtected(
        SilvaPermissions.AccessContentsInformation, 'get_filename')
    def get_filename(self):
        if self.hires_image is None:
            return self.getId()
        return self.hires_image.get_filename()

    security.declareProtected(
        SilvaPermissions.AccessContentsInformation, 'get_mime_type')
    def get_mime_type(self):
        if self.hires_image is None:
            return 'application/octet-stream'
        return self.hires_image.get_mime_type()

    security.declareProtected(
        SilvaPermissions.AccessContentsInformation, 'get_content_type')
    def get_content_type(self):
        if self.hires_image is None:
            return 'application/octet-stream'
        return self.hires_image.get_content_type()

    security.declareProtected(
        SilvaPermissions.AccessContentsInformation, 'get_file_size')
    def get_file_size(self):
        if self.hires_image is None:
            return 0
        return self.hires_image.get_file_size()

    ##########
    ## private

    def _create_derived_images(self):
        self._create_web_presentation()
        self._create_thumbnail()

    def _create_web_presentation(self):
        try:
            transformer = Transformer()
            cropbox = self.get_crop_box()
            if cropbox is not None:
                crop_rect = Rect.from_points(Point(cropbox[0], cropbox[1]),
                                             Point(cropbox[2], cropbox[3]))
                transformer.append(Crop(crop_rect))

            if self.web_scale != '100%':
                spec = WHResizeSpec.parse(self.web_scale)
                if spec is None:
                    spec = PercentResizeSpec.parse(self.web_scale)
                if spec is not None:
                    transformer.append(Resize(spec))

            image_io = transformer.transform(self.hires_image, self.web_format)
            if image_io:
                content_type = self._web2ct[self.web_format]
                self._image_factory('image', image_io, content_type)
            else:
                self.image = self.hires_image
        except ValueError as error:
            logger.error("Web presentation creation failed for %s with %s" %
                        ('/'.join(self.getPhysicalPath()), str(error)))
            self.image = self.hires_image
            return
        except IOError as error:
            logger.error("Web presentation creation failed for %s with %s" %
                        ('/'.join(self.getPhysicalPath()), str(error)))
            if str(error.args[0]) == "cannot read interlaced PNG files":
                self.image = self.hires_image
                return
            raise ValueError(str(error))

    def _create_thumbnail(self):
        try:
            transformer = Transformer(ThumbnailResize(self.thumbnail_size))
            thumb = transformer.transform(self.image or self.hires_image,
                                          self.web_format)
            if thumb:
                content_type = self._web2ct[self.web_format]
                self._image_factory('thumbnail_image', thumb, content_type)
        except IOError, e:
            logger.info("Thumbnail creation failed for %s with %s" %
                        ('/'.join(self.getPhysicalPath()), str(e)))
            if str(e.args[0]) == "cannot read interlaced PNG files":
                self.thumbnail_image = None
                return
            else:
                raise ValueError(str(e))
        except ValueError, e:
            logger.info("Thumbnail creation failed for %s with %s" %
                        ('/'.join(self.getPhysicalPath()), str(e)))
            # no thumbnail
            self.thumbnail_image = None
            return

    def _image_factory(self, identifier, stream, content_type=None):
        service_files = getUtility(IFilesService)
        new_image = service_files.new_file(identifier)
        setattr(self, identifier, new_image)
        new_image = getattr(self, identifier)
        new_image.set_file(stream, content_type)
        getUtility(IMimeTypeClassifier).guess_filename(new_image, self.getId())
        return new_image

    def _image_is_hires(self):
        return (self.image is not None and
                self.image.aq_base is self.hires_image.aq_base)


InitializeClass(Image)


# Management helpers

class ImageStorageConverter(object):
    """Convert image storage.
    """
    grok.implements(interfaces.IUpgrader)

    def __init__(self, service):
        self.service = service

    def validate(self, image):
        if not interfaces.IImage.providedBy(image):
            return False
        if image.hires_image is None:
            logger.error(
                "No orginal data for %s, storage not changed." %
                '/'.join(image.getPhysicalPath()))
            return False
        if self.service.is_file_using_correct_storage(image.hires_image):
            # don't convert that are already correct
            return False
        return True

    def upgrade(self, image):
        image_file = image.hires_image
        content_type = image_file.get_mime_type()
        data = image_file.get_file_fd()
        try:
            image._image_factory('hires_image', data, content_type)
            image._create_derived_images()
        finally:
            data.close()
        logger.info(
            "Storage for image %s converted" %
            '/'.join(image.getPhysicalPath()))
        return image


for mimetype in mimetypes.types_map.values():
    if mimetype.startswith('image'):
        mimetypeRegistry.register(mimetype, manage_addImage, 'Silva')


def image_factory(self, id, content_type, file):
    """Create an Image.
    """
    filename = None
    if hasattr(file, 'name'):
        filename = os.path.basename(file.name)
    id = mangle.Id(self, id or filename,
        file=file, interface=interfaces.IAsset)
    id.cook()
    if not id.isValid():
        return None
    img = Image(str(id)).__of__(self)
    return img


@grok.subscribe(interfaces.IImage, IObjectMovedEvent)
def image_added(image, event):
    if image is not event.object or event.newName is None:
        return
    guess_filename = getUtility(IMimeTypeClassifier).guess_filename
    for file_id in ('hires_image', 'image', 'thumbnail_image'):
        image_file = getattr(image, file_id, None)
        if image_file is None:
            continue
        guess_filename(image_file, event.newName)

