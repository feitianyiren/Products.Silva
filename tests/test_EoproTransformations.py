# Copyright (c) 2002 Infrae. All rights reserved.
# See also LICENSE.txt
#
# Testing of xml<->xhtml bidrectional conversions.
# this tests along with the module is intended to 
# work with python2.1 and python2.2 or better
# 
# $Revision: 1.7 $
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

sys.path.insert(0, '..')

try:
    sys.path.insert(0, '..')
    from transform.eopro2_11 import silva, html
except ImportError:
    from Products.Silva.transform.eopro2_11 import silva, html

# lazy, but in the end we want to test everything anyway

from xml.dom import minidom
#
# getting test content
#

class Base(unittest.TestCase):
    """ Check various conversions/transformations """

    def setUp(self):
        from transform.Transformer import EditorTransformer
        self.transformer = EditorTransformer('eopro2_11')

class Fixup(Base):
    """ Check that a missing body tag is handled gracefully """
    def _test_fixup_html(self):
        # XXX disabled test
        html_frag="""<h2 silva_origin="silva_document" silva_id="testid">titel</h2>
                     <h3 silva_origin="heading" silva_type="normal"></h3>"""

        htmlnode = self.transformer.target_parser.parse(html_frag)
        self.assert_(len(htmlnode.find('body'))==1)

class HTML2XML(Base):
    """ conversions from HTML-nodes to XML """

    def test_empty_list_title(self):
        """test that a list without a title and/or a 
           type attribute produces empty title and a type attr
        """
        html_frag ="""<body><ul><li>eins</li></ul></body>"""
        node = self.transformer.target_parser.parse(html_frag)
        self.assert_(not self.transformer.target_parser.unknown_tags)
        nodes = node.find('body')[0].find()
        nodes = nodes.conv()
        nodes = nodes.find('list')
        self.assert_(len(nodes)==1)
        node = nodes[0]
        title = node.find('title')
        self.assert_(title)
        title = title[0]
        self.assert_(title.isEmpty())
        self.assert_(node.attrs.has_key('type'))
        self.assert_(len(node.find('li'))==1)

    def test_no_title(self):
        """ check that an (almost) empty html still procudes 
            a sane document. 
        """
        html_frag ="""<body><ul><li>eins</li></ul></body>"""
        nodes = self.transformer.to_source(html_frag, {'id':'testid', 
                                                       'title':'testtitle'})
        self.assert_(not self.transformer.target_parser.unknown_tags)

    def test_heading_conversion(self):
        html_frag="""<body><h3>main title</h3><h4>sub title</h4></body>"""
        node = self.transformer.target_parser.parse(html_frag)
        self.assert_(not self.transformer.target_parser.unknown_tags)

        nodes = node.find('body')[0].find()
        # convert to silva
        nodes = nodes.conv()
        headings = nodes.find('heading')
        self.assert_(len(headings)==2)
        self.assert_(headings[0].attrs['type']=='normal')
        self.assert_(headings[1].attrs['type']=='sub')

    def test_default_heading_conversion(self):
        html_frag="""<body><h1>eins</h1><h2>zwei</h2><h3>drei</h3>
                     <h4>vier</h4><h5>fuenf</h5><h6>sechs</h6></body>"""
        htmlnode = self.transformer.target_parser.parse(html_frag)
        self.assert_(not self.transformer.target_parser.unknown_tags)

        node = htmlnode.convert(context={'id':u'', 'title':u''})

        doc = node.find('silva_document')[0].find('doc')[0]
        self.assert_(len(doc.find('heading'))==5)
        num_sub = 0
        num_normal = 0
        for heading in doc.find('heading'):
            if heading.attrs._type=='normal':
                num_normal+=1
            if heading.attrs._type=='sub':
                num_sub+=1
        self.assert_(num_normal==2) # h2 gets document title
        self.assert_(num_sub==3)

    def test_ol_list_conversion(self):
        html_frag="""<ol><h5>titel</h5><li>eins</li><li>zwei</li></ol>"""
        node = self.transformer.target_parser.parse(html_frag)
        self.assert_(not self.transformer.target_parser.unknown_tags)
        #node = node.find('body')[0]
        node = node.find('ol')[0]
        list_node = node.conv()
        self.assert_(list_node.name()=='list')
        self.assert_(list_node.attrs.has_key('type'))
        self.assert_(list_node.attrs['type']=='1')
        self.assert_(len(list_node.find('title'))==1)
        self.assert_(list_node.find('title')[0].extract_text()=='titel')
        self.assert_(len(list_node.find('li'))==2)

    def test_ul_list_conversion_with_inline_title(self):
        html_frag="""<ul><h5>titel</h5><li>eins</li><li>zwei</li></ul>"""
        node = self.transformer.target_parser.parse(html_frag)
        self.assert_(not self.transformer.target_parser.unknown_tags)
        #node = node.find('body')[0]
        node = node.find('ul')[0]
        list_node = node.conv()
        self.assert_(list_node.name()=='list')
        self.assert_(list_node.attrs.has_key('type'))
        self.assert_(list_node.attrs['type']=='disc')
        self.assert_(len(list_node.find('li'))==2)

    def test_ul_list_conversion_with_outer_title(self):
        html_frag="""<body><h5>titel</h5> <ul><li>eins</li><li>zwei</li></ul></body>"""
        node = self.transformer.target_parser.parse(html_frag)
        self.assert_(not self.transformer.target_parser.unknown_tags)
        node = node.find('body')[0].content
        #print 
        #print "source", node.asBytes()
        result = node.conv()
        list_node = result.find('list')
        #print "result", list_node.asBytes()
        self.assert_(len(list_node)==1)
        list_node = list_node[0]
        self.assert_(list_node.attrs.has_key('type'))
        self.assert_(list_node.attrs['type']=='disc')
        self.assert_(len(list_node.find('li'))==2)
        self.assert_(len(list_node.find('title'))==1)
        self.assert_(list_node.find('title')[0].content[0]==u'titel')

    def test_ignore_html(self):
        """ test that a html tag doesn't modify the silva-outcome """
        frag="""<body silva_id="test"><h2 silva_id="test">titel</h2><h3>titel</h3></body>"""
        node = self.transformer.target_parser.parse(frag)
        node = node.conv()

        frag2="""<html><head></head>%(frag)s</html>""" % locals()
        node2 = self.transformer.target_parser.parse(frag2)
        node2 = node2.conv()

        self.assertEquals(node, node2)



class RoundtripWithTidy(unittest.TestCase):
    """ Transform and validate with 'tidy' if available. Also do a roundtrip """
    def setUp(self):
        from transform.Transformer import Transformer 
        self.transformer = Transformer(source='eopro2_11.silva', target='eopro2_11.html')

    def _check(self, string):
        htmlnode = self.transformer.to_target(string)
        html = htmlnode.asBytes()
        self._checkhtml(html)
        silvanode = self.transformer.to_source(html)
        orignode = self.transformer.source_parser.parse(string)
        silvanode = silvanode.compact()
        orignode = orignode.compact()
        try:
            self.assertEquals(silvanode, orignode)
        except:
            print
            print orignode.asBytes()
            print html
            print silvanode.asBytes()
            raise
        return htmlnode
        
    def test_heading_and_p(self):
        simple = '''
        <silva_document id="test"><title>doc title</title>
        <doc>
           <heading type="normal">top title</heading>
           <p type="lead">lead paragraph</p>
           <heading type="sub">sub title</heading>
           <p type="normal">normal paragraph</p>
        </doc>
        </silva_document>'''
        self._check(simple)

    def test_heading_and_p_special_chars(self):
        simple = '''
        <silva_document id="test"><title>doc title</title>
        <doc>
           <heading type="normal">top title</heading>
           <p type="normal">&quot;&amp;&lt;&gt;&apos;</p>
        </doc>
        </silva_document>'''
        self._check(simple)

    def test_empty_list_title_produces_no_html_title(self):
        simple = '''
        <silva_document id="test"><title>doc title</title>
        <doc>
           <list type="disc"><title></title>
               <li>eins</li>
           </list>
        </doc>
        </silva_document>'''
        htmlnode = self.transformer.to_target(simple)
        body = htmlnode.find('body')[0]
        list = body.find('ul')
        self.assert_(len(list)==1)
        # check no title
        self.assert_(not list[0].find('h5'))
        # check roundtrip
        self._check(simple)

    def test_existing_list_title_produces_h5(self):
        simple = '''
        <silva_document id="test"><title>doc title</title>
        <doc>
           <list type="disc"><title>listtitle</title>
               <li>eins</li>
           </list>
        </doc>
        </silva_document>'''
        htmlnode = self.transformer.to_target(simple)
        body = htmlnode.find('body')[0]
        list = body.find('ul')
        self.assert_(len(list)==1)
        # check title
        self.assert_(len(body.find('h5'))==1)
        self.assert_(body.find('h5').extract_text()==u'listtitle')

    def _simplelist(self):
        return '''
        <silva_document id="test"><title>doc title</title>
        <doc>
           <list type="%s">
              <title>list title</title>
              <li>eins</li>
              <li>zwei</li>
              <li>drei</li>
           </list>
        </doc>
        </silva_document>'''

    def test_list_disc(self):
        self._check(self._simplelist() % 'disc')
    def test_list_circle(self):
        self._check(self._simplelist() % 'circle')
    def test_list_square(self):
        self._check(self._simplelist() % 'square')
    def test_list_a(self):
        self._check(self._simplelist() % 'a')
    def test_list_i(self):
        self._check(self._simplelist() % 'i')
    def test_list_1(self):
        self._check(self._simplelist() % '1')
    def test_list_none(self):
        self._check(self._simplelist() % 'none')

    def _check_modifier(self, htmltag, silvatag):
        """ check that given markups work """
        silvadoc = '''<silva_document id="test"><title></title>
                        <doc><p type="normal">
                             <%(silvatag)s>text</%(silvatag)s>
                             </p>
                        </doc>
                      </silva_document>''' % locals()
        htmlnode = self._check(silvadoc)
        body = htmlnode.find('body')[0]
        p = body.find('p')[0]
        htmlmarkup = p.find(htmltag)
        self.assert_(len(htmlmarkup)==1)
        htmlmarkup = htmlmarkup[0]
        self.assert_(htmlmarkup.extract_text()=='text')

    def test_modifier_b(self):
        self._check_modifier('b','strong')

    def test_modifier_em(self):
        self._check_modifier('i','em')

    def test_modifier_underline(self):
        self._check_modifier('u','underline')

    def test_link_with_absolute_url(self):
        """ check that a link works """
        silvadoc = '''<silva_document id="test"><title>title</title>
                        <doc><p type="normal">
                             <link url="http://www.heise.de">linktext</link>
                             </p>
                        </doc>
                      </silva_document>''' 
        htmlnode = self._check(silvadoc)
        body = htmlnode.find('body')[0]
        p = body.find('p')[0]
        a = p.find('a')
        self.assert_(len(a)==1)
        a = a[0]
        self.assert_(a.attrs.get('href')=='http://www.heise.de')
        self.assert_(a.content.asBytes()=='linktext')

    def test_image(self):
        """ check that the image works"""
        silvadoc = '''<silva_document id="test"><title>title</title>
                        <doc><p type="normal">
                             <image image_path="/path/to/image"></image>
                             </p>
                        </doc>
                      </silva_document>''' 
        htmlnode = self._check(silvadoc)
        body = htmlnode.find('body')[0]
        p = body.find('p')[0]
        img = p.find('img')
        self.assert_(len(img)==1)
        img = img[0]
        self.assert_(img.attrs.get('src')=='/path/to/image')

    def _checkhtml(self, html):
        cmd = 'tidy -eq -utf8'
        try:
            import popen2
            stdout, stdin, stderr = popen2.popen3(cmd)
	    stdin.write(html)
	    stdin.close()
	    output = stderr.read()
	    stderr.close()
	    stdout.close()
        except IOError:
            # print "tidy doesn't seem to be available, skipping html-check"
            return

        for line in output.split('\n'):
            if line.startswith('line') and line.find('Error')!=-1:
                raise AssertionError, "to_xhtml produced html errors, this is what i got\n" + html


def equiv_node(node1, node2):
    assert(node1.nodeName==node2.nodeName)
    assert(node1.nodeValue==node2.nodeValue)
    attrs1 = node1.attributes
    attrs2 = node2.attributes

    assert_len(attrs1, attrs2)
    
    childs1 = node1.childNodes
    childs2 = node2.childNodes

    assert_len(childs1, childs2)

    for c1 in childs1:
        ok=0
        for c2 in childs2:
            try:
                equiv_node(c1,c2)
                ok=1
                break
            except AssertionError, error:
                continue

        if not ok:
            #print "problem with", c1, "on", node1,node2
            raise AssertionError

#
# invocation of test suite
#
        
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Fixup,'test'))
    suite.addTest(unittest.makeSuite(HTML2XML, 'test'))
    suite.addTest(unittest.makeSuite(RoundtripWithTidy, 'test'))
    return suite
    
def main():
    unittest.TextTestRunner().run(test_suite())

if __name__ == '__main__':
    main()
