# qgis_uldk
Python script for QGIS for downloading parcel vector layers using ULDK API of The Central Office of Geodesy and Cartography of Poland

# Instructions
In QGIS select a vector layer and run the script to obtain a temporary layer representing parcels found within the input layer.

Tested for the following CRS types of the input layer: EPSG:2176, EPSG:2177, EPSG:2178, EPSG:2179, EPSG:2180.

The output layer is in EPSG:2180. The features have two attributes: the parcel's TERYT identifier and the parcel's number.
