# Copyright (c) 2002-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import unittest

from zope.interface.verify import verifyObject
from zope.publisher.browser import TestRequest

from Products.Silva.testing import FunctionalLayer, TestCase
from Products.Silva.tests.helpers import open_test_file
from Products.Silva.silvaxml import xmlimport

from Products.Silva.transform.interfaces import IRenderer
from Products.Silva.transform.rendererreg import getRendererRegistry
from Products.Silva.transform.renderer.imagesonrightrenderer import ImagesOnRightRenderer

from lxml import etree

expected_html = '\n<table>\n  <tr>\n    <td valign="top"><h2 class="heading">This is a rendering test</h2>\n                <p class="p">\n                    This is a test of the XSLT rendering functionality.\n                </p>\n            </td>\n    <td valign="top">\n      <a href="http://nohost/root/silva_xslt/bar.html">\n        <img src="http://nohost/root/silva_xslt/foo" />\n      </a>\n      <br />\n    </td>\n  </tr>\n</table>\n'


class ImagesOnRightRendererTest(TestCase):
    layer = FunctionalLayer

    def setUp(self):
        self.root = self.layer.get_application()
        self.layer.login('editor')
        with open_test_file("test_document2.xml") as source_document:
            xmlimport.importFromFile(source_document, self.root)
        self.document = self.root.test_document
        self.request = TestRequest()

    def _get_renderer_images_on_right(self):
        registry = getRendererRegistry()
        silva_doc_renderers = registry.getRenderersForMetaType('Silva Document')
        self.failUnless(len(silva_doc_renderers) != 0)
        self.failUnless('Images on Right' in silva_doc_renderers)
        return silva_doc_renderers['Images on Right']

    def test_implements_renderer_interface(self):
        renderer = self._get_renderer_images_on_right()
        self.failUnless(verifyObject(IRenderer, renderer))

    def test_renders_images_on_right(self):
        renderer = self._get_renderer_images_on_right()
        self.assertXMLEqual(
            renderer.transform(self.document, self.request),
            expected_html)

    def test_error_handling(self):

        class BrokenImagesOnRightRenderer(ImagesOnRightRenderer):
            def __init__(self):
                super(BrokenImagesOnRightRenderer, self).__init__(
                    'data/images_to_the_right_broken.xslt', __file__)

        renderer = BrokenImagesOnRightRenderer()
        self.assertRaises(
            etree.XMLSyntaxError,
            renderer.transform, self.document, self.request)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ImagesOnRightRendererTest))
    return suite
