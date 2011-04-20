from five import grok

from silva.core import interfaces
from Products.SilvaMetadata.Index import MetadataCatalogingAttributes


class CatalogingAttributes(MetadataCatalogingAttributes):
    grok.context(interfaces.ISilvaObject)

    @property
    def publication_status(self):
        return 'public'


class CatalogingAttributesPublishable(CatalogingAttributes):
    grok.context(interfaces.IPublishable)

    @property
    def publication_status(self):
        if self.context.is_published(update_status=False):
            return 'public'
        if self.context.is_approved(update_status=False):
            return 'approved'
        return 'unapproved'


class CatalogingAttributesVersion(CatalogingAttributes):
    grok.context(interfaces.IVersion)

    @property
    def publication_status(self):
        """Returns the status of the current version
        Can be 'unapproved', 'approved', 'public', 'last_closed' or 'closed'
        """
        content = self.context.get_content()
        status = None
        unapproved_version = content.get_unapproved_version(False)
        approved_version = content.get_approved_version(False)
        public_version = content.get_public_version(False)
        previous_versions = content.get_previous_versions()
        if unapproved_version and unapproved_version == self.context.id:
            status = "unapproved"
        elif approved_version and approved_version == self.context.id:
            status = "approved"
        elif public_version and public_version == self.context.id:
            status = "public"
        else:
            if previous_versions and previous_versions[-1] == self.context.id:
                status = "last_closed"
            elif self.context.id in previous_versions:
                status = "closed"
            else:
                # this is a completely new version not even registered
                # with the machinery yet
                status = 'unapproved'
        return status

