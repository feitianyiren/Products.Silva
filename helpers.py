# Copyright (c) 2002 Infrae. All rights reserved.
# See also LICENSE.txt
# $Revision: 1.9 $
# Zope
from AccessControl import ModuleSecurityInfo
# Silva interfaces
from IVersioning import IVersioning
from IContainer import IContainer
# python
import string, re, urllib

p_ID = re.compile(r'^(.*?)([0-9]+)$')
def getNewId(old_id):
    """returns an id based on the old id

        if old_id ends with a number, the number is increased, 
        otherwise 2 is appended
    """
    
    m = p_ID.match(old_id)
    if m is None: return '%s2' % (old_id, )
    
    name = m.group(1)
    count = int(m.group(2))
    
    return "%s%i" % (name, count+1)
    

def add_and_edit(self, id, REQUEST):
    """Helper function to point to the object's management screen if
    'Add and Edit' button is pressed.
    id -- id of the object we just added
    """
    if REQUEST is None:
        return
    try:
        u = self.DestinationURL()
    except:
        u = REQUEST['URL1']
    if REQUEST.has_key('submit_edit'):
        u = "%s/%s" % (u, urllib.quote(id))
    REQUEST.RESPONSE.redirect(u+'/manage_main')

def unapprove_helper(object):
    """Unapprove object and anything unapprovable contained by it.
    """
    if IVersioning.isImplementedBy(object):
        if object.is_version_approved():
            object.unapprove_version()
    if IContainer.isImplementedBy(object):
        for item in object.get_ordered_publishables():
            unapprove_helper(item)
    
def unapprove_close_helper(object):
    """Unapprove/close object and anything unapprovable/closeable contained by it.
    """
    if IVersioning.isImplementedBy(object):
        if object.is_version_approved():
            object.unapprove_version()
        if object.is_version_published():
            object.close_version()
    if IContainer.isImplementedBy(object):
        default = object.get_default()
        if default:
            unapprove_close_helper(default)
        for item in object.get_ordered_publishables():
            unapprove_close_helper(item)

# this is a bit of a hack; using implementation details of ParsedXML..
from Products.ParsedXML.PrettyPrinter import _translateCdata, _translateCdataAttr

translateCdata = _translateCdata
translateCdataAttr = _translateCdataAttr

#
# This code is not here to stay. It is an experimental "proof of concept"
# implementation for resticting view access on Silva objects based on
# ip addresses. We need a more generic approach integrated in the silva core
# e.g. based on roles?
#
# This code is based on Clemens Klein-Robbenhaar's "CommentParser.py" 
# Marc Petitmermet's and Wolfgang Korosec's code.
#
security = ModuleSecurityInfo('Products.Silva.helpers')
security.declarePublic('parseAccessRestriction')

__all__ = ('parseAccessRestriction',)

ACCESS_RESTRICTION_PROPERTY = 'access_restriction'

# match any quote _not_ preceeded by a backslash
quote_split = re.compile(r'(?<![^\\]\\)"', re.M)

# match any escapes of quotes (e.g. \\ or \" )
drop_escape = re.compile(r'\\(\\|")')

def parseAccessRestriction(item):
    raw_string = ''
    #if item.implements_container():
    # use "getattr" to get aquired access restrictions.
    raw_string = getattr(item, ACCESS_RESTRICTION_PROPERTY, '')
    #elif item.implements_versioned_content():
    #    raw_string = item.getProperty(DOCUMENT_PROPERTY, '')
    if not raw_string: return {}

    return _parse_raw(raw_string)

#stupid record
class State:
    pass

def _parse_raw(raw_string):
    props = {}

    state = State()
    
    # first split due to quotes
    quoted = quote_split.split(raw_string)

    in_quote = None
    state.read_props = None

    for item in quoted:
        if in_quote:
            _parse_quote(item, state, props)
        else:
            _parse_unquote(item, state, props)
            
        in_quote = not in_quote
    
    return props


def _parse_unquote(something, state, props):
    
    if not state.read_props:
        try:
            name, something = map (string.strip, something.split(':',1) )
        except ValueError:
            # no name: quit.
            return
        state.name = name
        props[name] = []
        state.plist = props[name]
        state.read_props = 1

    separate = something.split(';',1)
    if len(separate) > 1:
        something, rest = map (string.strip, separate)
    else:
        rest=None

    for p in map (string.strip, something.split(',') ):
        if p:
            state.plist.append(p)

    if rest is not None:
        state.read_props=None
        _parse_unquote(rest, state, props)


def _parse_quote(something, state, props):
    """ parse everything enclosed in quotes.
    this is an easy one: just remove the escapes
    """
    if not state.read_props:
        raise ValueError, "not inside a property definition: <<%s>>" % something

    something = drop_escape.sub(lambda match: match.group(1), something )
    state.plist.append(something)
    

def test():
    """ hacky: test by hand ..."""
    test1 = r"""
property: value1, "my quote, comma containing value", 
"another value with \"quotes\" in it, as well as commas", "something containing \\", even more;

property2: aha, what's that, ";;;" ,,,'ignores commas',"",;

single: only one property  ;

white: "  one property,  whitespace preserving   ";

"""

    props1 = {'property': ['value1','my quote, comma containing value',
                           'another value with "quotes" in it, as well as commas',
                           'something containing \\', 'even more'] ,
              'property2': [ 'aha', "what's that", ';;;', "'ignores commas'",'' ] ,
              'single' : [ 'only one property' ],
              'white' : ["  one property,  whitespace preserving   "],
              }
                          
    props = _parse_raw(test1)

    if not props1 == props:
        print "FAILURE:\n expected %s\n but got %s\n" %  tuple(map(str, (props1, props) ))
    else:
        print "simple test ok"

# self testing:
if __name__ == '__main__':
    test()
