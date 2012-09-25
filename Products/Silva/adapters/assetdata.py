# -*- coding: utf-8 -*-
# Copyright (c) 2002-2012 Infrae. All rights reserved.
# See also LICENSE.txt

from five import grok
from silva.core import interfaces


class FileData(grok.Adapter):
    grok.implements(interfaces.IAssetData)
    grok.context(interfaces.IFile)

    def getData(self):
        return self.context.get_file()


class ImageData(grok.Adapter):
    grok.implements(interfaces.IAssetData)
    grok.context(interfaces.IImage)

    def getData(self):
        image = getattr(self.context, 'hires_image', None)
        if image is None:
            # Fallback to 'normal' image, which, if there isn't a hires
            # version, should be the original.
            image = self.context.image
        return image.get_file()

