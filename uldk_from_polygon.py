# imports
import requests

# select a vector layer to work with
layer = iface.activeLayer()

transformations = {
    2176: '+proj=pipeline +step +inv +proj=tmerc +lat_0=0 +lon_0=15 +k=0.999923 +x_0=5500000 +y_0=0 +ellps=GRS80 +step +proj=tmerc +lat_0=0 +lon_0=19 +k=0.9993 +x_0=500000 +y_0=-5300000 +ellps=GRS80',
    2177: '+proj=pipeline +step +inv +proj=tmerc +lat_0=0 +lon_0=18 +k=0.999923 +x_0=6500000 +y_0=0 +ellps=GRS80 +step +proj=tmerc +lat_0=0 +lon_0=19 +k=0.9993 +x_0=500000 +y_0=-5300000 +ellps=GRS80',
    2178: '+proj=pipeline +step +inv +proj=tmerc +lat_0=0 +lon_0=21 +k=0.999923 +x_0=7500000 +y_0=0 +ellps=GRS80 +step +proj=tmerc +lat_0=0 +lon_0=19 +k=0.9993 +x_0=500000 +y_0=-5300000 +ellps=GRS80',
    2179: '+proj=pipeline +step +inv +proj=tmerc +lat_0=0 +lon_0=24 +k=0.999923 +x_0=8500000 +y_0=0 +ellps=GRS80 +step +proj=tmerc +lat_0=0 +lon_0=19 +k=0.9993 +x_0=500000 +y_0=-5300000 +ellps=GRS80',
}

# get layer's crs
current_crs = layer.crs()
current_srid = current_crs.postgisSrid()

target_crs = QgsCoordinateReferenceSystem('EPSG:2180')
target_srid = target_crs.postgisSrid()

# reproject layer if needed
if current_crs !=target_crs:
    result = processing.run("native:reprojectlayer", 
        {'INPUT':layer,
        'TARGET_CRS':QgsCoordinateReferenceSystem('EPSG:2180'),
        'OPERATION':transformations[current_srid],
        'OUTPUT':'TEMPORARY_OUTPUT'})
    layer = result['OUTPUT']
    print(f'CRS changed from {current_crs} to {target_crs}')
else:
    print(f'Current CRS: {target_crs}')

print('Work in progress...')

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
    'CRS': target_crs,
    'OUTPUT':'TEMPORARY_OUTPUT'})
    
grid = results['OUTPUT']

results = processing.run("native:clip", 
    {'INPUT':grid,
    'OVERLAY':buffer,
    'OUTPUT':'TEMPORARY_OUTPUT'})

rpoints = results['OUTPUT']

# create the target layer
found_parcels = QgsVectorLayer('Polygon', 'parcels', 'memory')
found_parcels.setCrs(target_crs)
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
    response = requests.get(f'https://uldk.gugik.gov.pl/?request=GetParcelByXY&xy={coord.x()},{coord.y()}&result=geom_wkt,teryt,parcel')
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

# check for the completeness of the output layer
result = processing.run("native:difference", 
    {'INPUT':layer,
    'OVERLAY':found_parcels,
    'OUTPUT':'TEMPORARY_OUTPUT',
    'GRID_SIZE':None})

missing = result['OUTPUT']

result = processing.run("native:multiparttosingleparts", 
    {'INPUT':missing,
    'OUTPUT':'TEMPORARY_OUTPUT'})
    
missing = result['OUTPUT']

result = processing.run("native:randompointsinpolygons", 
    {'INPUT':missing,
    'POINTS_NUMBER':1,
    'MIN_DISTANCE':0,
    'MIN_DISTANCE_GLOBAL':0,
    'MAX_TRIES_PER_POINT':10,
    'SEED':None,
    'INCLUDE_POLYGON_ATTRIBUTES':True,
    'OUTPUT':'TEMPORARY_OUTPUT'})
    
rpoints = result['OUTPUT']

# loop until complete
while rpoints.featureCount() > 0:
    first_point = next(rpoints.getFeatures())
    geom = first_point.geometry()
    coord = geom.asPoint()
    response = requests.get(f'https://uldk.gugik.gov.pl/?request=GetParcelByXY&xy={coord.x()},{coord.y()}&result=geom_wkt,teryt,parcel') # ,{srid}&result
    r = response.content
    
    rstring = str(r, encoding='utf-8').split('\n')[1].split(';')[1]
    geom_wkt, teryt, parcel = rstring.split('|')
    f = QgsFeature(found_parcels.fields())
    f.setAttributes([teryt, parcel])
    geometry = QgsGeometry.fromWkt(geom_wkt)
    f.setGeometry(geometry)
    
    provider.addFeature(f)
    found_parcels.updateExtents()
    
    result = processing.run("native:difference", 
    {'INPUT':layer,
    'OVERLAY':found_parcels,
    'OUTPUT':'TEMPORARY_OUTPUT',
    'GRID_SIZE':None})

    missing = result['OUTPUT']
    
    result = processing.run("native:multiparttosingleparts", 
        {'INPUT':missing,
        'OUTPUT':'TEMPORARY_OUTPUT'})
        
    missing = result['OUTPUT']
    
    result = processing.run("native:randompointsinpolygons", 
        {'INPUT':missing,
        'POINTS_NUMBER':1,
        'MIN_DISTANCE':0,
        'MIN_DISTANCE_GLOBAL':0,
        'MAX_TRIES_PER_POINT':10,
        'SEED':None,
        'INCLUDE_POLYGON_ATTRIBUTES':True,
        'OUTPUT':'TEMPORARY_OUTPUT'})
        
    rpoints = result['OUTPUT']


# load the results
QgsProject.instance().addMapLayer(found_parcels)

print('Done')



