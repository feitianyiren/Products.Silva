##bind context=context
##parameters=asset_context, asset
# $Id: asset_lookup_path_mangler.py,v 1.1.4.2 2003/03/19 09:45:46 zagy Exp $

asset_context = asset_context.split('/')
asset_path = asset.getPhysicalPath()
return '/'.join(context.path_mangler(asset_context, asset_path))

