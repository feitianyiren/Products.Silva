from Interface import Interface

class IViewerSecurity(Interface):
    def setAcquired():
        """Set minimum viewer role restriction to acquire from above.
        """
        
    def setMinimumRole(role):
        """Set the minimum (viewer) role needed for view permission here.

        If role is Anonymous, viewer role restriction will be set to
        acquire from above.
        """

    def isAcquired():
        """Check whether minimum role is acquired.
        """
        
    def getMinimumRole():
        """Get the minimum role needed for view permission here.
        """

    def getMinimumRoleAbove():
        """Get the minimum role needed for view permission in parent.
        """

class ILockable(Interface):
    def createLock():
        """Create lock for context object.

        Return false if already locked, otherwise true.
        """

    def breakLock():
        """Break the lock.
        """

    def isLocked():
        """Check whether this object is locked by another user.
        """

class IArchiveFileImporter(Interface):
    def importArchive(archivefile, assettitle=None, recreatedirs=1):
        """Import archive file
        
        Use 'assettitle' for the title to set on all assets created
        
        According to the recreatedirs setting, create a substructure of
        Silva Containers (probably Silva Folders) reflecting the structure
        of the archive file. This substructure will be created relative to
        the adapted context.
        
        Return a tuple with the list of succeeded items and failed items
        providing feedback on what archive contents have succesfully been 
        imported into Silva Assets and what contents have not.
        """

class IZipfileImporter(Interface):
    def isFullmediaArchive(zipname):
        """Tests if the zip archive is a fullmedia archive
        """

    def importFromZip(context, zipname, settings):
        """Import Silva content from a full media zip file.

        context -- The content object to be imported into
        zipname -- The filename of the zip archive
        settings -- The import settings
        """

class IZipfileExporter(Interface):
    def exportToZip(context, zipname, settings):
        """Export Silva content to a zip file.
        
        context -- The content object to be exported
        zipname -- The filename of the zip archive
        settings -- The export settings
        """

class IAssetData(Interface):
    def getData():
        """ Get actual data stored for this asset as calling index_html()
        for assets can have all kinds of unwanted side effects.
        """        

class IVersionManagement(Interface):
    def getVersionById(id):
        """get a version by id"""

    def getPublishedVersion():
        """return the current published version, None if it doesn't exist"""

    def getUnapprovedVersion():
        """return the current unapproved (editable) version, None if it doesn't exist"""

    def getApprovedVersion():
        """return the current approved version, None if it doesn't exist"""

    def revertEditableToOld(id):
        """revert editable to an older version

            the current editable will become the last closed (last closed will
            move to closed list), if there's a published version that will
            not be changed.
            can raise AttributeError when no editable version is available
            (XXX what to do when there is an approved version?)
        """

    def getVersionIds():
        """return a list of all version ids"""

    def getVersions(sort_attribute='id'):
        """return a list of version objects
        
            if sort_attribute resolves to False, no sorting is done,
            by default it sorts on id converted to int (so [0,1,2,3,...]
            instead of [0,1,10,2,3,...] if values < 20)
        """

    def deleteVersion(id):
        """delete a version

            can raise AttributeError when the version doesn't exist, 
            VersioningError if the version is approved(XXX?) or published
        """

    def deleteOldVersions(number_to_keep):
        """delete all but <number_to_keep> last closed versions

            can be called only by managers, and should be used with great care,
            since it can potentially remove interesting versions
        """
    
