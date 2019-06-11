from osgeo import ogr, osr, gdal
import os
import numpy as np
import cv2
import WFSHandling as wfs
from Params import (PIXELSIZE, IMAGE_SIZE, IMAGE_SIZE_SMALL, EDGES_EXTENT,
                    BBOX_EXTENT, NO_DATA_VALUE)


class GeometryConverter():
    '''
        class for the Convertion of Geometry data to raster arrays, that uses
        the WFSHandling.Feldblock_WFS class for finding Geometry data
    '''

    def __init__(self):
        # start the WFS
        self.fb_wfs = wfs.Feldblock_WFS()
        # create the spatial reference
        self.srs = osr.SpatialReference()
        self.srs.ImportFromEPSG(5650)

    def __makeShapefile(self, geometries, filename, filter="POLYGON"):
        '''
            Save the Geometries into a new ESRI Shapefile with the specified
            name

            Parameters
            ----------
            geometries: Geometry[]
                - the list of geometries to be saved
            filename: String
                - name for the shapefile (without '.shp')
            filter: string
                - "LINESTRING" or "POLYGON"

            Returns
            -------
            number of geometries saved
        '''
        shp_driver = ogr.GetDriverByName('ESRI Shapefile')
        source = shp_driver.CreateDataSource(filename + '.shp')
        # create the layer
        if filter == "POLYGON":
            layer = source.CreateLayer("geometries", self.srs, ogr.wkbPolygon)
        else:
            layer = source.CreateLayer("geometries", self.srs,
                                       ogr.wkbLineString)

        def addFeature(geometry, layer):
            '''
                Adds the geometry to the shapefile layer
            '''
            if geometry.IsEmpty():
                return
            feature = ogr.Feature(layer.GetLayerDefn())
            feature.SetGeometry(geometry)
            layer.CreateFeature(feature)

        # Process the text file, add the features to the shapefile
        i = 0
        for g in geometries:
            if g.GetGeometryName() == filter:
                addFeature(g, layer)
                i += 1
            else:
                for geom in g:
                    addFeature(geom, layer)
                    i += 1
        # Save and close the data source
        source = None
        return i

    def __convertShapefile2RasterArray(self, filename, keepFile=False):
        '''
            Converts the layer of a shapefile to a raster data array

            Parameters:
            ----------
            filename: string
                - name of the shapefile without this.NAME_EXTENT + '.shp'
            keepFile: Boolean (optional)
                - whether or not to produce a file representing the shapefile
                  with the name 'filename.shp'
                - default: False

            Returns:
            -------
            the array containing the image data
        '''
        # Open the source layer and read out the extent
        source = ogr.Open(filename + '.shp')
        source_layer = source.GetLayer()
        x_min, x_max, y_min, y_max = source_layer.GetExtent()
        x_size = int(np.max([round((x_max - x_min) / PIXELSIZE), 1]))
        y_size = int(np.max([round((y_max - y_min) / PIXELSIZE), 1]))

        edgeFile = filename + EDGES_EXTENT + '.tif'

        # Create the destination data source
        rast_driver = gdal.GetDriverByName('GTiff')
        data = rast_driver.Create(edgeFile, x_size, y_size, 1,
                                  gdal.GDT_Byte, ['NBITS=1'])
        data.SetGeoTransform((x_min, PIXELSIZE, 0, y_max, 0, -PIXELSIZE))

        band = data.GetRasterBand(1)
        band.SetNoDataValue(NO_DATA_VALUE)
        # rasterize and get array
        gdal.RasterizeLayer(data, [1], source_layer, burn_values=[1])
        array = band.ReadAsArray()
        data.GetRasterBand(1).WriteArray(array)

        # at this point geometries may not fill the whole bbox, so we need to
        # fix that
        # transform array to the wanted size
        bbox = getBBoxForTifFile(filename + '.tif')
        x = int(round((x_min - bbox[0]) / PIXELSIZE))
        y = int(round((bbox[3] - y_max) / PIXELSIZE))
        raster = np.zeros((IMAGE_SIZE_SMALL, IMAGE_SIZE_SMALL))
        raster[y:y + y_size, x:x + x_size] = array

        data = None
        deleteShapefile(filename)
        if not keepFile:
            os.remove(edgeFile)
        return raster

    def __geometries2RasterArray(self, geometries, file, keepFile=False,
                                 filter="POLYGON"):
        '''
            Convert geometry list to raster data array (and save it)

            Parameters
            ----------
            geometries: Geometry[]
                - the list of LineStrings to be saved
            file: String
                - name for the edge file without '.tif'
            filter: string
                - "LINESTRING" oder "POLYGON"

            Returns
            -------
            the array containing the image data
        '''
        if self.__makeShapefile(geometries, file, filter) == 0:
            return getEmptyRasterArray(file)
        raster = self.__convertShapefile2RasterArray(file, keepFile=keepFile)
        if len(raster.shape) == 3:
            return raster[:, :, 0]
        return raster

    def bbox2EdgeMap(self, bbox, file, keepEdgeMapFile=False):
        '''
            Get the raster of the EdgeMap for the provided bounding Box

            Parameters
            ----------
            bbox: float[xmin, ymin, xmax, ymax]

            file: string
                - name for the edge file without the EXTENT and without '.tif'

            Returns
            -------
            the raster array containing the Edge within the BBox
            None - if no Polygon from the WFS is intersecting the BBox
        '''
        geometriesInBBox = self.fb_wfs.findGeometries(bbox)
        if len(geometriesInBBox):
            return None
        # print('WFS found', len(geometriesInBBox), 'geometries for', bbox)
        raster = self.__geometries2RasterArray(geometriesInBBox, file,
                                               keepFile=keepEdgeMapFile,
                                               filter="LINESTRING")
        if keepEdgeMapFile:
            cv2.imwrite(file + EDGES_EXTENT + '.tif', raster)
        # print('dots made: ', sum(sum(raster)), '/',
        # len(raster)*len(raster[0]), ' -> ',
        # sum(sum(raster))/len(raster)/len(raster[0]), '%\n')
        return raster

    def bbox2geometryRasters(self, bbox, file, manipulate=False):
        '''
            Gives the boundary and classification rasters of the EdgeMap for
            the provided bounding box once without manipulation, once with
            manipulation

            Parameters
            ----------
            bbox: float[xmin, ymin, xmax, ymax]

            file: string
                - name for the edge file without the EXTENT and without '.tif'

            manipulate: boolean
                - whether the Geometries underwent a manipulation

            Returns
            -------
            2 lists representing the rasters:
                1st: EdgeMap raster
                2nd: 3 channel (FB, LE, NBF) classification raster
        '''
        if '22' in file:
            print('still fein')
        fb, le, nbf, boundaries = self.fb_wfs.findGeometriesByGroup(bbox,
                                                                    manipulate)

        if '22' in file:
            print('auch gut', len(fb), len(le), len(nbf))
        raster_fb = self.__geometries2RasterArray(fb, file) * 255
        raster_le = self.__geometries2RasterArray(le, file) * 255
        raster_nbf = self.__geometries2RasterArray(nbf, file) * 255

        shape = (raster_fb.shape[0], raster_fb.shape[1], 1)
        raster_groups = np.concatenate((raster_fb.reshape(shape),
                                        raster_le.reshape(shape),
                                        raster_nbf.reshape(shape)), 2)

        raster_bound = self.__geometries2RasterArray(boundaries, file,
                                                     filter="LINESTRING") * 255

        return raster_bound, raster_groups


def deleteShapefile(file):
    '''
        delete the data sources for that Shapefile

        Parameters
        ---------
        file: string
            - filename without '.shp'
    '''
    if os.path.exists(file + '.shp'):
        os.remove(file + '.dbf')
        os.remove(file + '.prj')
        os.remove(file + '.shp')
        os.remove(file + '.shx')


def getEmptyRasterArray(file, keepFile=False):
    '''
        produces an empty raster array, same sized as the given file

        Parameters
        ----------
        file: String
            - name for the edge file without the EXTENT and without '.tif'

        Returns
        -------
        the 0-filled array
    '''
    # calculate array size
    x_min, y_min, x_max, y_max = getBBoxForTifFile(file + '.tif')
    x_size = int((x_max - x_min) / PIXELSIZE)
    y_size = int((y_max - y_min) / PIXELSIZE)

    empty_raster = np.zeros((x_size, y_size))
    if keepFile:
        edgeFile = file + EDGES_EXTENT + '.tif'
        cv2.imwrite(edgeFile, empty_raster)
    deleteShapefile(file)
    return empty_raster


def getNoClassRaster(raster):
    '''
        returns a raster array, with values 0, if the raster a None-0-value at
        that position, and 255 if the raster array has only zeros

        Parameters
        ----------
        raster: the 3 channel classification raster
    '''
    shape = (raster.shape[0], raster.shape[1], 1)
    raster_nothing = np.zeros(shape)
    for i in range(shape[0] - 1):
        for j in range(shape[1] - 1):
            if sum(raster[i, j]) == 0:
                raster_nothing[i, j] = 255
    return raster_nothing


def getBBoxForTifFile(file):
    '''
        Extracts the BBox for the file

        Parameters
        ----------
        file: string
            - the file which should be opened
            - like 'path/to/this/filename.tif'

        Returns
        -------
        - the BBox of the imagefile
        - [xmin, ymin, xmax, ymax] in meters to the respective Coordinate
        System
    '''
    try:
        fileC = file[:-3] + "tfw"
        f = open(fileC, 'r')
        textArray = f.readlines()
        xmin = float(textArray[4][:len(textArray[4]) - 2])
        ymax = float(textArray[5][:len(textArray[4]) - 2])
        return [xmin, ymax - IMAGE_SIZE, xmin + IMAGE_SIZE, ymax]
    except FileNotFoundError:
        try:
            fileC = file[:-7] + BBOX_EXTENT
            f = open(fileC, 'r')
        except FileNotFoundError:
            fileC = file[:-4] + BBOX_EXTENT
            f = open(fileC, 'r')
        textArray = f.readlines()
        xmin = float(textArray[0])
        ymin = float(textArray[1])
        xmax = float(textArray[2])
        ymax = float(textArray[3])
        return [xmin, ymin, xmax, ymax]
