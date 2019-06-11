# pixel size of the input images in meters
PIXELSIZE = 0.2
# length/ height of the input images in meters
IMAGE_SIZE = 2000
# number of pixel on each axis for the smaller images
IMAGE_SIZE_SMALL = 480
# the extension for the saved BBOX txt file
BBOX_EXTENT = '_bbox.txt'
# extension for the DOM
DOM_EXTENT = '_dom'
# the extension for the saved Shapefile and the EdgeMap
EDGES_EXTENT = '_edges'
# extension for FB, LE, NBF classification raster
GROUPS_EXTENT = '_groups'
# extension for no data area classification
NO_DATA_AREA_EXTENT = '_nothing'
# default value to insert for generating the edge maps
NO_DATA_VALUE = 0
# path to the images on the portable harddrive
PATH_DISK = '/media/robin/Seagate Expansion Drive/DOP_20_RGB/'
# path to the DOPs
DOP_PATH = '/home/robin/workspace/Masterarbeit/data/DOP/'
# not scaled, 10000x10000 pixels
BIG_DOP_TRAIN = 'images/train/'
BIG_DOP_TEST = 'images/test/'
# scaled, 480x480 pixels
SMALL_DOP_TRAIN = 'smaller_images/train/'
SMALL_DOP_TEST = 'smaller_images/test/'
# folger for canny edge detection
CANNY_FOLDER = 'canny/'
# folder for Roberts/Sobel Image
SOBEL_ROBERTS_FOLDER = 'sobel_roberts/'
# WFS for Feldblockkataster
WFS_FELDBLOCK = 'https://www.geodaten-mv.de/dienste/gdimv_feldblock_wfs'
# WMS for Digitales Oberflächenmodell
WMS_DOM = 'https://www.geodaten-mv.de/dienste/dom_wms'
