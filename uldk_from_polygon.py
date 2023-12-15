# imports
import requests

# select a vector layer to work with
layer = iface.activeLayer()

# set the coordinate reference system
srid = 2180
crs = QgsCoordinateReferenceSystem(f'EPSG:{srid}')

# create a layer of request points
results = processing.run("native:buffer", 
    {'INPUT':layer,
    'DISTANCE':20,
    'SEGMENTS':5,
    'END_CAP_STYLE':0,
    'JOIN_STYLE':0,
    'MITER_LIMIT':2,
    'DISSOLVE':False,
    'OUTPUT':'TEMPORARY_OUTPUT'})
    
buffer = results['OUTPUT']

spacing = 10 # spacing for the grid layer

results = processing.run("native:creategrid",
    {'TYPE':0,
    'EXTENT':buffer,
    'HSPACING':spacing,
    'VSPACING':spacing,
    'HOVERLAY':0,
    'VOVERLAY':0,
    'CRS':crs,
    'OUTPUT':'TEMPORARY_OUTPUT'})
    
grid = results['OUTPUT']

results = processing.run("native:clip", 
    {'INPUT':grid,
    'OVERLAY':buffer,
    'OUTPUT':'TEMPORARY_OUTPUT'})

rpoints = results['OUTPUT']

# create the target layer
found_parcels = QgsVectorLayer('Polygon', 'parcels', 'memory')
found_parcels.setCrs(crs)
provider = found_parcels.dataProvider()

# add attributes to the layer
provider.addAttributes([QgsField('teryt', QVariant.String), QgsField('parcel', QVariant.String)])
found_parcels.updateFields()

# iterate over request points
# send requests based on a request point's coordinates
# update request points layer to avoid duplicate parcels
while rpoints.featureCount() > 0:
    first_point = next(rpoints.getFeatures())
    geom = first_point.geometry()
    coord = geom.asPoint()
    response = requests.get(f'https://uldk.gugik.gov.pl/?request=GetParcelByXY&xy={coord.x()},{coord.y()},{srid}&result=geom_wkt,teryt,parcel')
    r = response.content
    
    rstring = str(r, encoding='utf-8').split('\n')[1].split(';')[1]
    geom_wkt, teryt, parcel = rstring.split('|')
    f = QgsFeature(found_parcels.fields())
    f.setAttributes([teryt, parcel])
    geometry = QgsGeometry.fromWkt(geom_wkt)
    f.setGeometry(geometry)
    
    provider.addFeature(f)
    found_parcels.updateExtents()
    
    processing.run("native:selectbylocation", 
        {'INPUT':rpoints,
        'PREDICATE':[0],
        'INTERSECT':found_parcels,
        'METHOD':0})
    
    with edit(rpoints):
        rpoints.deleteSelectedFeatures()

# load the results
QgsProject.instance().addMapLayer(found_parcels)
















