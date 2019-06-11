from owslib.wfs import WebFeatureService as WFS
from owslib.util import ResponseWrapper
from six.moves import cStringIO
from xml.etree import ElementTree as ET
from osgeo import ogr
import re
import Params
import random


class Feldblock_WFS():
    '''
        class for usage of the Feldblock WFS for Mecklenburg-Western-Pommerania
    '''

    def __init__(self):
        self.mv = '{http://www.geodaten-mv.de/dienste/gdimv_feldblock_wfs}'
        self.gml = '{http://www.opengis.net/gml}'

        self.fb_layer = 'mv:feldbloecke'
        self.le_layer = 'mv:landschaftselemente'
        self.nbf_layer = 'mv:nbf_flaechen'
        self.layers = [self.fb_layer, self.le_layer, self.nbf_layer]

        self.wfsUrl = Params.WFS_FELDBLOCK
        self.wfsVersion = '1.1.0'

        self.wfs = WFS(url=self.wfsUrl, version=self.wfsVersion)
        assert self.wfs is not None, "Could not connect to WFS"
        # __printWFSInfos(wfs)

        random.seed(5)

    def __getFeatures(self, typeName):
        '''
            Gets the Features with the WFS

            Parameters
            ----------
            typeName: string
                - name of the FeatureType to search for
            bbox: float[xmin, ymin, xmax, ymax]
        '''
        feat = self.wfs.getfeature(typename=typeName, bbox=self.bbox)
        if isinstance(feat, ResponseWrapper):
            feat = feat.read()
        if isinstance(feat, cStringIO):
            feat = feat.getvalue()
        return feat

    def __printWFSInfos(self):
        print('Titel:\t' + self.wfs.identification.title)
        print('Operationen:\t' +
              str([operation.name for operation in self.wfs.operations]))
        print('FetaureTypes:\t' + str(list(self.wfs.contents)))
        print('GetCapabilities:\t' + self.wfs.getcapabilities().geturl())

    def __findGeometries(self, feature_xml):
        '''
            Find the Geometries within the XML-string

            Parameters
            ----------
            feature_xml: string
                - the returned XML string from our WFS containing the
                geometries

            Returns
            -------
            Geometry[] containing the geometries found
        '''
        root = ET.fromstring(feature_xml)
        # print(root.tag)
        geometries = []
        for child in root.findall(self.gml + 'featureMember'):
            for cchild in child[0].find(self.mv + 'the_geom')[0][0]:
                # print (cchild.text)
                geom_gml = str(ET.tostring(cchild, method='xml'))
                # print("String Ding:\n",geom_gml)

                # Start
                geom_gml = re.sub(r"b'<", "<", geom_gml)
                # Middle
                geom_gml = re.sub(r">[^>^<]+<^/", "><", geom_gml)
                # End
                geom_gml = re.sub(r">[^>]*'", ">", geom_gml)

                geom = ogr.CreateGeometryFromGML(geom_gml)
                if geom is None:
                    print("Problem with GML:\n", geom_gml)
                    print("Geometry:\n", geom)
                geometries.append(geom)
        # print(len(geometries), " geometries in gml")
        return geometries

    def __manipulate(self):
        '''
            Manipulates the lists given
            one of the following scenarios will happen:
                1. a LE or NBF geometry will be absorbed by the surrounding FB
                2. a random Polygon will be added to either LE or NBF and the
                specified area will be deleted from the other layers
            the scenario is randomly chosen, but if #1 is not possible #2 will
            happen
        '''
        # scenario 1: LE or NBF absorbed
        for element in self.nbf:
            for geom in self.fb:
                union = geom.Union(element)
                if union.GetGeometryName() == 'POLYGON':
                    self.nbf.remove(element)
                    self.fb.remove(geom)
                    self.fb.append(union)
                    return

        for element in self.le:
            for geom in self.fb:
                union = geom.Union(element)
                if union.GetGeometryName() == 'POLYGON':
                    self.le.remove(element)
                    self.fb.remove(geom)
                    self.fb.append(union)
                    return

        # scenario 2: random Polygon added
        xmin, ymin, xmax, ymax = self.bbox
        x = [(xmax - xmin) * random.random() + xmin for i in [0, 1, 2]]
        y = [(ymax - ymin) * random.random() + ymin for i in [0, 1, 2]]
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(x[0], y[0])
        ring.AddPoint(x[1], y[1])
        ring.AddPoint(x[2], y[2])
        ring.AddPoint(x[0], y[0])

        polygon = ogr.Geometry(ogr.wkbPolygon)
        polygon.AddGeometry(ring)
        for feldblock in self.fb:
            intersection = polygon.Intersection(feldblock)
            if not intersection.IsEmpty():
                if intersection.GetGeometryName() == 'POLYGON':
                    intersection = [intersection]
                for g in intersection:
                    difference = feldblock.Difference(g)
                    self.fb.remove(feldblock)
                    self.fb.append(difference)
                    rand = random.random()
                    if rand < 1 / 3:
                        self.le.append(g)
                    if rand >= 2 / 3:
                        self.nbf.append(g)
                    return

        self.fb.append(polygon)

    def __cap2BBoxBoundaries(self, geometryList, justBoundaries=True):
        '''
            Caps the Geometries (geometric intersection) in the list to the
            boundaries of the BBox

            Parameters
            ----------
            geometryList: Geometry[]
                - the geometries to be capped
            bbox: float[xmin, ymin, xmax, ymax]
            justBoundaries: boolean
                - whether the LineString boundaries or the Polygon areas are
                returned

            Returns
            -------
            a list containing all capped geometries, maybe empty
        '''
        if len(geometryList) == 0:
            return geometryList
        bboxPolygon = maxMin2Polygon(self.bbox)
        result = []
        for g in geometryList:
            try:
                if justBoundaries:
                    g = g.GetBoundary()
                g = g.Intersection(bboxPolygon)
                result.append(g)
            except AttributeError:
                for geom in g:
                    if justBoundaries:
                        geom = geom.GetBoundary()
                    geom = geom.Intersection(bboxPolygon)
                    result.append(geom)
        return result

#    def __getGeometriesInBBox(self, layer, bbox):
#        '''
#            returns the capped polygonal geometries returned by the wfs for
#            that layer
#        '''
#        polygons = self.__findGeometries(self.__getFeature(layer, bbox))
#        return self.cap2BBoxBoundaries(polygons, bbox, justBoundaries=False)

    def findGeometries(self, bbox, cap2Boundaries=True):
        '''
            Find the Geometries within the BBox

            Parameters
            ----------
            bbox: float[xmin, ymin, xmax, ymax]
            cap2Boundaries: Boolean
                - whether or not cap the found geometries to the bboxBoundaries

            Returns
            -------
            a list containing all geometries found within the BBox
            None - if no geometries are found
        '''
        assert len(bbox) == 4, "BBox needs exactly 4 values"

        self.bbox = bbox
        g = self.__findGeometries(self.__getFeatures(self.fb_layer))
        g.append(self.__findGeometries(self.__getFeatures(self.le_layer)))
        g.append(self.__findGeometries(self.__getFeatures(self.nbf_layer)))
        if len(g) == 0:
            return None
        if cap2Boundaries:
            g = self.__cap2BBoxBoundaries(g)
        return g

    def findGeometriesByGroup(self, bbox, manipulate=False):
        '''
            Find the Geometries within the BBox

            Parameters
            ----------
            bbox: float[xmin, ymin, xmax, ymax]
            manipulate: boolean
                - whether the geometries should be manipulated

            Returns
            -------
            4 lists containing all geometries found within the BBox:
                1st: Feldblock Polygons
                2nd: Landschaftselement Polygons
                3rd: Nicht beihilfefähige Flächen Polygons
                4th: Boundaries of all 4

        '''
        assert len(bbox) == 4, "BBox needs exactly 4 values"

        self.bbox = bbox
        self.fb = self.__findGeometries(self.__getFeatures(self.fb_layer))
        self.le = self.__findGeometries(self.__getFeatures(self.le_layer))
        self.nbf = self.__findGeometries(self.__getFeatures(self.nbf_layer))

        if manipulate:
            self.__manipulate()

        geometries = self.fb
        geometries.append(self.le)
        geometries.append(self.nbf)
        self.fb = self.__cap2BBoxBoundaries(self.fb, justBoundaries=False)
        self.le = self.__cap2BBoxBoundaries(self.le, justBoundaries=False)
        self.nbf = self.__cap2BBoxBoundaries(self.nbf, justBoundaries=False)
        boundaries = self.__cap2BBoxBoundaries(geometries)
        return self.fb, self.le, self.nbf, boundaries


def maxMin2Polygon(coordinateList):
    '''
        Get Rectangle Polygon for the BBox Coordinates in the list

        Parameters
        ----------
        coordinateList: float[x1, y1, x2, y2]

        Returns
        -------
        Polygon representing the Rectangle from the BBox Coordinates
    '''
    assert len(coordinateList) >= 4, "not enough coordinates"
    x1, y1, x2, y2 = coordinateList[0:4]

    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint(x1, y1)
    ring.AddPoint(x1, y2)
    ring.AddPoint(x2, y2)
    ring.AddPoint(x2, y1)
    ring.AddPoint(x1, y1)

    polygon = ogr.Geometry(ogr.wkbPolygon)
    polygon.AddGeometry(ring)
    return polygon
