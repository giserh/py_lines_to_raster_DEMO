'''
MIT License
Copyright (c) 2019 Ivan D'Ortenzio
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Created on 25/03/2019

@author: Ivan D'Ortenzio
'''

import fiona
from osgeo import gdal
from osgeo import osr
from shapely.geometry import shape
from shapely.geometry import MultiLineString
from PIL import Image
from PIL import ImageDraw
from PIL import ImageOps

# This function converts lon/lat to screen x/y coords
def lonlat_to_xy(lon,lat):
    xc = int((lon - lonmin)*(out_w/(lonmax - lonmin)));
    yc = int((latmax - lat)*(out_h/(latmax - latmin)));
    return xc,yc

# https://download.bbbike.org/osm/bbbike/
in_shp = "SF_roads_clip.shp"
out_raster = in_shp.split(".")[0]+".tif"

src_ds = fiona.open(in_shp)

# Get the EPSG code
src_ds_epsg = int(src_ds.crs['init'].split(":")[1])

# Create osr SpatialReference from EPSG
gcp_srs = osr.SpatialReference()
gcp_srs.ImportFromEPSG(src_ds_epsg)

# Export SpatialReference to WKT
gcp_crs_wkt = gcp_srs.ExportToWkt()

# Dataset extent
lonmin,latmin,lonmax,latmax = src_ds.bounds

# The width/height of output image
out_w = int((lonmax - lonmin)*1.11e5) if gcp_srs.IsGeographic() else int((lonmax - lonmin))
out_h = int((latmax - latmin)*1.11e5) if gcp_srs.IsGeographic() else int((latmax - latmin))

# Create a blank gray image
img = Image.new('L', (out_w+1, out_h+1))

# Create a draw object that can be used to draw lines in the given image
draw = ImageDraw.Draw(img)
    
# Iterate src_ds features
for fc in src_ds:
    # fc geometry
    geom = shape(fc['geometry'])
    
    # MultiLineString case
    if isinstance(geom,MultiLineString):
        # iterate MultiLineString segments
        for line in geom:
            # Get LineString lon/lat coordinates
            lon,lat = line.xy            
            lonlat = zip(lon,lat)
            
            # Convert lon/lat to screen x/y
            coords = [lonlat_to_xy(lon,lat) for lon,lat in lonlat]
            
            # Draw a rasterized line from collected coordinates
            draw.line(coords, fill=255)
    # LineString case
    else:
        # Get LineString lon/lat coordinates
        lon,lat = geom.xy            
        lonlat = zip(lon,lat)
        
        # Convert lon/lat to screen x/y
        coords = [lonlat_to_xy(lon,lat) for lon,lat in lonlat]
                
        # Draw a rasterized line from collected coordinates
        draw.line(coords, fill=255)
        
# Invert the image - Just for visualization purpose
img = ImageOps.invert(img)

# Save the output image to disk
img.save(out_raster)
        
# Georeference the output image using GDAL - We use corners coordinates of the input vector extent to do that...
in_ds = gdal.Open(out_raster,1)

# lon/lat corners coordinates to screen x/y coords
pxmin,pymin = lonlat_to_xy(lonmin,latmin)
pxmax,pymax = lonlat_to_xy(lonmax,latmax)

# x,y,z=0,px,py
ll = (lonmin,latmin,0,pxmin,pymin) # LowerLeft
lr = (lonmax,latmin,0,pxmax,pymin) # LowerRight
ul = (lonmin,latmax,0,pxmin,pymax) # UpperLeft
ur = (lonmax,latmax,0,pxmax,pymax) # UpperRight

# Create GCPs
gcp_ll = gdal.GCP(*ll)
gcp_lr = gdal.GCP(*lr)
gcp_ul = gdal.GCP(*ul)
gcp_ur = gdal.GCP(*ur)

# Set raster projection
in_ds.SetProjection(gcp_crs_wkt)
# Set raster GCPs
in_ds.SetGCPs([gcp_ll,gcp_lr,gcp_ul,gcp_ur],gcp_crs_wkt)
# Set NoData as 255
in_ds.GetRasterBand(1).SetNoDataValue(255)
is_ds = None