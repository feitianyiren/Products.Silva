# Copyright (c) 2002 Infrae. All rights reserved.
# See also LICENSE.txt
# $Revision: 1.4 $
from ISilvaObject import ISilvaObject
from IPublishable import IPublishable

class IContent(ISilvaObject, IPublishable):    
    """An object that can be published directly and would appear
    in the table of contents. Can be ordered.
    """
    # ACCESSORS
    def get_content():
        """Used by acquisition to get the nearest containing content object.
        PUBLIC
        """
        pass

    def content_url():
        """Used by acquisition to get the URL of the containing content object.
        PUBLIC
        """
        pass
    
    def is_default():
        """True if this content object is the default content object of
        the folder.
        PUBLIC
        """
        pass

    def get_indexables():
        """Return a list of ParsedXML documents (that can be indexed
        in various ways). May return the empty list if there is nothing
        to index.
        """
        pass

