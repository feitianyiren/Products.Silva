# -*- coding: utf-8 -*-
# Copyright (c) 2011 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import unittest

from Products.Silva.testing import FunctionalLayer
from Products.Silva.tests.helpers import open_test_file


class FileCatalogTestCase(unittest.TestCase):
    layer = FunctionalLayer

    def setUp(self):
        self.root = self.layer.get_application()
        self.layer.login('editor')

        with open_test_file('dark_energy.txt') as data:
            factory = self.root.manage_addProduct['Silva']
            factory.manage_addFile('universe', u'Not related to Silva', data)

    def search(self, **kwargs):
        return map(lambda b: (b.getPath(), b.publication_status),
                   self.root.service_catalog(**kwargs))

    def test_fulltext(self):
        """Content and title of the file is indexed in its fulltext.
        """
        self.assertItemsEqual(
            self.search(fulltext='dark energy'),
            [('/root/universe', 'public')])
        self.assertItemsEqual(
            self.search(fulltext='silva'),
            [('/root/universe', 'public')])

    def test_rename(self):
        """A file is reindexed if it is renamed.
        """
        self.root.manage_renameObject('universe', 'renamed_universe')
        self.assertItemsEqual(
            self.search(fulltext='dark energy'),
            [('/root/renamed_universe', 'public')])

    def test_rename_title(self):
        """A file whose the title changed is reindexed.
        """
        self.root.universe.set_title(u'All true in Zope')
        self.assertItemsEqual(
            self.search(fulltext='silva'),
            [])
        self.assertItemsEqual(
            self.search(fulltext='zope'),
            [('/root/universe', 'public')])

    def test_moving(self):
        """A moved filed is reindexed.
        """
        factory = self.root.manage_addProduct['Silva']
        factory.manage_addPublication('publication', 'Publication')
        token = self.root.manage_cutObjects(['universe'])
        self.root.publication.manage_pasteObjects(token)
        self.assertItemsEqual(
            self.search(path='/root'),
            [('/root', 'unapproved'),
             ('/root/publication', 'unapproved'),
             ('/root/publication/universe', 'public')])

    def test_copy(self):
        """A copy of a file is indexed.
        """
        token = self.root.manage_copyObjects(['universe'])
        self.root.manage_pasteObjects(token)
        self.assertItemsEqual(
            self.search(fulltext='dark energy'),
            [('/root/universe', 'public'),
             ('/root/copy_of_universe', 'public')])

    def test_deletion(self):
        """A file is unindex when it is removed.
        """
        self.root.manage_delObjects(['universe'])
        self.assertItemsEqual(
            self.search(path='/root'),
            [('/root', 'unapproved')])
        self.assertItemsEqual(
            self.search(fulltext='dark energy'),
            [])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(FileCatalogTestCase))
    return suite