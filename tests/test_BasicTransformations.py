# Copyright (c) 2002 Infrae. All rights reserved.
# See also LICENSE.txt
#
# Testing of xml<->xhtml bidrectional conversions.
# this tests along with the module is intended to 
# work with python2.1 and python2.2 or better
# 
# $Revision: 1.5 $
import unittest

# 
# module setup
#
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO 

try:
    from xml.parsers import expat 
except ImportError:
    from xml.parsers.pyexpat import expat

import sys,os

try:
    sys.path.insert(0, '..')
    from transform.ObjectParser import ObjectParser
    from transform.eopro2_11 import silva
    from transform import base
except ImportError:
    import Zope
    from Products.Silva.transform.ObjectParser import ObjectParser
    from Products.Silva.transform.eopro2_11 import silva
    from Products.Silva.transform import base

# lazy, but in the end we want to test everything anyway

from xml.dom import minidom
#
# getting test content
#

def get_test_content(name):
    """ get testing content from the 'files' directory
    """
    tmp = os.path.dirname(os.path.abspath(sys.argv[0]))
    fn = os.path.join(tmp, 'files', name)
    f = open(fn, 'rb')
    s = f.read()
    f.close()
    return s


class SilvaXMLObjectParser(unittest.TestCase):
    """ See that Construction of the object tree from silva-xml works """
    def setUp(self):
        self.parser = ObjectParser(silva)

        self.basicdoc = '''<silva_document id="test">
                                <title>testtitle</title>
                                <doc/>
                             </silva_document>'''

    def find_exactly_one(self, node, tag):
        res = node.find(tag)
        self.assert_(len(res)==1)
        return res[0]

    def test_silva_basic_document(self):
        node = self.parser.parse(self.basicdoc)
        self.assert_(not self.parser.unknown_tags)
        node = self.find_exactly_one(node, 'silva_document')
        self.assert_(node.attrs['id'] == 'test')
        title = self.find_exactly_one(node, 'title')
        self.assert_(title.content.asBytes()=='testtitle')
        self.find_exactly_one(node, 'doc')

    def test_processinginst(self):
        """ test that processing instruction goes through the parser """
        node = self.parser.parse('<?xml version="1.0" encoding="UTF-8" ?><silva_document/>')
        self.assert_(node.find('silva_document'))

    def test_attribute(self):
        """ test that attribute lookup basically works """
        node = self.parser.parse('<silva_document id="whatever"/>')
        node = node[0]
        self.assert_(node.attrs._id)
        self.assert_(node.attrs['id'])
        try: node.attrs['notexists']
        except KeyError: pass
        else: 
            raise AssertionError, "access to non-existent attribute didn't raise exception"
        try: node.attrs._notexists
        except AttributeError: pass
        else: 
            raise AssertionError, "access to non-existent attribute didn't raise exception"

    def test_inequality_operator(self):
        s1= '<silva_document><title>my title</title></silva_document>'
        s2= ' <silva_document>  <title>my title</title></silva_document>'
        node1 = self.parser.parse(s1)
        node2 = self.parser.parse(s2)
        self.assert_(node1 != node2)

        # test bogus comparison
        self.assert_(node1 != 3)
        self.assert_(node1 != "hall")

    def test_equality_operator(self):
        s1= '<silva_document><title>my title</title></silva_document>'
        s2= '<silva_document><title>my title</title></silva_document>'
        node1 = self.parser.parse(s1)
        node2 = self.parser.parse(s2)
        self.assert_(node1==node1)
        self.assert_(node1==node2)

    def test_plain_text_as_content_with_asBytes(self):
        s1= '<p type="normal">blabla</p>'
        node1 = self.parser.parse(s1)

        p = node1.find('p')[0]
        node2 = p.__class__(
            'mytext',
            type = p.attrs._type
            )
        self.assert_(node2.content.asBytes()=='mytext')

    def test_method_find(self):
        node = self.parser.parse(self.basicdoc)

        self.assert_(node.find('silva_document'))
        self.assertEquals(node.find('silva_document'),
                          node.find(silva.silva_document))
        sdoc = node.find('silva_document')[0]
        self.assert_(sdoc.find('doc'))
        self.assertEquals(sdoc.find('doc'),
                          sdoc.find(silva.doc))

    def test_method_find_and_partition(self):
        doc = '''<doc>
                  <heading type="normal">normal</heading>
                  <p type="normal">p</p>
                  <heading type="sub">sub</heading>
               </doc>'''

        node = self.parser.parse(doc)
        node = node.compact()
        node = node.find('doc')[0]
        pre,match,post = node.find_and_partition('p')
        #print "pre",pre.asBytes()
        #print "match",match.asBytes()
        #print "post",repr(post), post.asBytes()

        self.assert_(len(pre)==1)
        self.assert_(pre[0].name()=='heading')
        self.assert_(match.name()=='p')
        self.assert_(len(post)==1)
        self.assert_(post[0].name()=='heading')

        pre,match,post = node.find_and_partition('list')
        self.assert_(isinstance(match, base.Element))
        self.assert_(not match)
        self.assert_(not post)
        self.assert_(len(post)==0)


    def test_method_compact(self):
        node= self.parser.parse(self.basicdoc)
        self.assert_(node.compact())
       
    def test_simple_dogfood_roundtrip(self):
        node= self.parser.parse(self.basicdoc)
        # looses processing instruction
        newstring = node.asBytes()
        node2 = self.parser.parse(newstring)
        self.assert_(node==node2)

    def test_method_compact(self):
        node= self.parser.parse(self.basicdoc)
        self.assert_(node.compact())
        # should traverse the tree

    def test_text_nodes_with_control_characters(self):
        ustring = u'''\x22\x27&<>'''
        node = base.Text(ustring)
        s = node.asBytes(encoding='utf8')
        self.assertEquals(s, '&quot;&apos;&amp;&lt;&gt;')

    def test_ignore_unknown_tags(self):
        """ test that ignore_unknown contains unknown tags """
        s1= '<doc><xtag attr="test"><p>test</p></xtag></doc>'
        node1 = self.parser.parse(s1)
        doc = node1.find('doc')[0]
        self.assert_(not doc.find('xtag'))
        self.assert_(len(self.parser.unknown_tags)==1)
        self.assert_(self.parser.unknown_tags[0]=='xtag')

        p = doc.find('p')
        self.assert_(len(p)==1)
        self.assert_(p[0].content.asBytes()=='test')

#
# invocation of test suite
#
        
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SilvaXMLObjectParser))
    return suite
    
def main():
    unittest.TextTestRunner().run(test_suite())

if __name__ == '__main__':
    main()
