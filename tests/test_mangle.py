# Copyright (c) 2002, 2003 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id: test_mangle.py,v 1.1 2003/08/07 14:52:30 zagy Exp $

import Zope
Zope.startup()

import unittest
from StringIO import StringIO

from Products.Silva import mangle
from Products.Silva.interfaces import IAsset
from Products.Silva.tests.base import SilvaTestCase



class MangleTest(SilvaTestCase):

    def setUp(self):
        SilvaTestCase.setUp(self)
        self.folder = folder = self.addObject(self.silva, 'Folder', 'fold',
            title='fold', create_default=0)
        self.addObject(folder, 'SimpleContent', 'a_content',
            title='a_content')
        self.addObject(folder, 'File', 'an_asset', title='an_asset',
            file=StringIO("foobar"))
    
    def test_validate(self):
        id = mangle.Id(self.folder, 'some_id')
        self.assertEquals(id.validate(), id.OK)
        
        id = mangle.Id(self.folder, 'a_content')
        self.assertEqual(id.validate(), id.IN_USE_CONTENT)
   
        id = mangle.Id(self.folder, 'an_asset')
        self.assertEqual(id.validate(), id.IN_USE_ASSET)
   
        id = mangle.Id(self.folder, 'a_content', allow_dup=1)
        self.assertEqual(id.validate(), id.OK)
   
        id = mangle.Id(self.folder, 'an_asset', allow_dup=1)
        self.assertEqual(id.validate(), id.OK)
        
        id = mangle.Id(self.folder, 'service_foobar')
        self.assertEqual(id.validate(), id.RESERVED_PREFIX)
   
        id = mangle.Id(self.folder, '&*$()')
        self.assertEqual(id.validate(), id.CONTAINS_BAD_CHARS)
        
        id = mangle.Id(self.folder, 'index_html')
        self.assertEqual(id.validate(), id.RESERVED)
   
        id = mangle.Id(self.folder, 'index')
        self.assertEqual(id.validate(), id.OK)
   
        id = mangle.Id(self.folder, 'index', interface=IAsset)
        self.assertEqual(id.validate(), id.RESERVED)
   
        an_asset = self.folder.an_asset
        id = mangle.Id(self.folder, 'index', instance=an_asset)
        self.assertEqual(id.validate(), id.RESERVED)
    
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(MangleTest))
    return suite

def main():
    unittest.TextTestRunner().run(test_suite())

if __name__ == '__main__':
    main()
    
