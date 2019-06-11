import cv2
from tifffile import imsave
from pathlib import Path
import matplotlib.pyplot as plt
import glob
import re
import sys
import os.path
import timeit
import codecs
import numpy as np
import GeometryConvertion as gc
import WMSHandling as wms
import Params
from Params import (GROUPS_EXTENT, EDGES_EXTENT, BBOX_EXTENT, IMAGE_SIZE_SMALL,
                    PIXELSIZE, DOP_PATH, SMALL_DOP_TRAIN, DOM_EXTENT)
# import random


class ImageProcessor():
    '''
        class that processes one big Image to smaller pieces
    '''

    def __init__(self, ImagePath):
        self.bigFile = ImagePath
        self.bigBBox = gc.getBBoxForTifFile(ImagePath)
        self.xmin, self.ymin, self.xmax, self.ymax = self.bigBBox
        self.bigImage = openImageFile(ImagePath)

        imageName = re.compile(r'(dop20.*).tif')
        self.imageName = imageName.search(self.bigFile).group(1)

        self.converter = gc.GeometryConverter()

    def __saveSmallerBBox(self, file, bbox):
        '''
            Saves the BBox for the previously produced smaller image

            Parameters
            ----------
            file: string
                - the path of the smaller image with its name
                - like 'path/to/this/filename' without '.tif'

            bbox: float[xmin, ymin, xmax, ymax]
                - in meters to the (Coordinate System)
        '''
        assert len(bbox) == 4, 'wrong BBox argument size'
        filename = file + BBOX_EXTENT
        text_file = open(filename, "w")
        for value in bbox:
            text_file.write(str(value) + '\n')
        text_file.close()

    def __save(self, smallImage, name, bbox, forTraining=True,
               for2ndNet=False):
        '''
            Gets the edge map and dom map and saves them, along the bbox and
            the image itself

            # degrees: (0=0, 1=90, 2=180, 3=270)
            # flip: (f=flipped up'n'down , n=no flip)

            Parameters
            ----------
            smallImage: the image-like matrix

            name: where the shortcuts will be added to

            bbox: float[xmin, ymin, xmax, ymax]

            forTraining: boolean
                - if true: if there is no geometry within the bbox, the images
                won't be saved
        '''
        self.__saveSmallerBBox(name, bbox)
        if for2ndNet:
            # true data
            edge_map, groups = self.converter.bbox2geometryRasters(bbox, name)
            # no Geometry Data found
            if np.max(groups) == 0:
                os.remove(name + BBOX_EXTENT)
                return
            cv2.imwrite(name + GROUPS_EXTENT + '.tif', groups)
            if '22' in name:
                print('schicki heinz')
            # make false data
            f_em, f_g = self.converter.bbox2geometryRasters(bbox, name, True)
            if '22' in name:
                print(f_em)
            cv2.imwrite(name + GROUPS_EXTENT + '_f.tif', f_g)
            cv2.imwrite(name + EDGES_EXTENT + '_f.tif', f_em)

        else:
            edge_map = gc.bbox2EdgeMap(bbox, name)
        if edge_map is None:
            if forTraining:
                os.remove(name + BBOX_EXTENT)
                return
            else:
                edge_map = gc.getEmptyRasterArray(name)

        cv2.imwrite(name + '.tif', smallImage)
        wms.getDOMMap4ImageAndSaveAsPNG(name + '.tif', bbox)
        cv2.imwrite(name + EDGES_EXTENT + '.tif', edge_map)

    def process(self, dirTo, forTraining, size_wanted, for2ndNet):
        '''
            starts producing smaller images and finding all other needed raster
            arrays
        '''
        assert len(size_wanted) == 2, 'need 2 dimensional size'
        x = size_wanted[0]
        y = size_wanted[1]

        ranX = int(self.bigImage.shape[0] / x)
        ranY = int(self.bigImage.shape[1] / y)

        height = x * PIXELSIZE
        length = y * PIXELSIZE

        # name of the specific image
        print(self.imageName)
        newFilename = dirTo + self.imageName

        for i in range(0, ranX):
            newBBox = [self.xmin + i * length, 0,
                       self.xmin + (i + 1) * length, 0]
            for j in range(0, ranY):
                image_ij = self.bigImage[(j * y): ((j + 1) * y),
                                         (i * x): ((i + 1) * x)]
                newName = newFilename + '_' + str(i * ranY + j + 1)
                newBBox[1] = self.ymax - (j + 1) * height
                newBBox[3] = self.ymax - j * height
                self.__save(smallImage=image_ij, name=newName, bbox=newBBox,
                            forTraining=forTraining, for2ndNet=for2ndNet)


def openImageFile(file):
    '''
        Reads the Image from the given filename

        Parameters
        ----------
        file: string
            - the file which should be opened
            - like 'path/to/this/filename.tif'

        Returns
        ------
        the image matrix
    '''
    # image = cv2.imread(file, cv2.IMREAD_LOAD_GDAL)
    image = cv2.imread(file)
    if image is None:
        print("Unable to open " + file)
        sys.exit()
    return image


def openEdgeImage(file):
    '''
        Reads the edge image for the given TIF-File

        Parameters
        ----------
        file: string
            - the file which should be opened
            - like 'path/to/this/filename.tif'

        Returns
        ------
        the edge image stored in 'path/to/this/filename_edges.tif'
    '''
    filename = file[:-4] + EDGES_EXTENT + '.tif'
    if os.path.exists(filename):
        return openImageFile(filename)
    return np.zeros((IMAGE_SIZE_SMALL, IMAGE_SIZE_SMALL))


#    if not flipNRotate:
#        return

    # for flipping and rotating images, if necessary
#    for angle in [1, 2, 3]:
#        imName = name + '_' + str(angle) + '_'
#        im = np.rot90(image, angle)
#        imsave(imName + 'n.tif', im)
#        im_f = np.flipud(im)
#        imsave(imName + 'f.tif', im_f)
#
#        em = np.rot90(edge_map, angle)
#        imsave(imName + 'n' + EDGES_EXTENT + '.tif', em)
#        em_f = np.flipud(em)
#        imsave(imName + 'f' + EDGES_EXTENT + '.tif', em_f)


def makeSmallerImages(path, dirTo=DOP_PATH + SMALL_DOP_TRAIN,
                      size_wanted=[IMAGE_SIZE_SMALL], forTraining=False,
                      for2ndNet=False):
    '''
        Reads the Tif-Images from the given path and produce smaller images.
        The belonging Edge Maps will also be produced

        NOTE: to exclude the areas that are not of our interest,
        we just save images, if their belonging bbox gives wfs geometries

        Parameters
        ----------
        path: string
            - the path to take the files from

        size_wanted: int[]
            - dimension of the output images
            - minimum size 1

        forTraining: boolean
    '''
    assert len(size_wanted) >= 1, 'no image size'
    x = size_wanted[0]
    y = size_wanted[0]
    if len(size_wanted) >= 2:
        y = size_wanted[1]
    # random.seed(3)

    Path(dirTo).mkdir(exist_ok=True)
    filenames = glob.glob(path + '*.tif')
    for f in filenames:
        if EDGES_EXTENT in f:
            continue
        imageProcessor = ImageProcessor(f)
        imageProcessor.process(dirTo=dirTo, size_wanted=[x, y],
                               forTraining=forTraining, for2ndNet=for2ndNet)
    print('Finished producing smaller images.')


def plotImageList(im_list, title_list, gray_list):
    '''
        plots the images with the corresponding titles to std out,
        lists need same length

        Parameters
        ----------
        im_list: list of array like image data
            - 3 channels
            - values range between 0 an 1
        title_list: list of strings
            - titles corresponding to the specific image
        gray_list: list of int
            - contains array positions to be plotted gray
    '''
    assert len(im_list) == len(title_list), 'not the same list lengths'
    fig, ax_array = plt.subplots(nrows=1, ncols=len(im_list), figsize=(12, 4),
                                 sharex=True, sharey=True)

    for i in range(len(im_list)):
        if i in gray_list:
            ax_array[i].imshow(im_list[i], cmap=plt.cm.gray)
        else:
            ax_array[i].imshow(im_list[i])
        ax_array[i].axis('off')
        ax_array[i].set_title(title_list[i], fontsize=16)

    fig.tight_layout()
    plt.show()


def showImageInWindow(image, text='An Image'):
    '''
        Opens a window and shows the given image. Any key will close the window
    '''
    cv2.imshow(text, image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def produceImageList(directory, fileName, withEdgeMaps=True):
    '''
        produces a list for the images in this directory (not recursive)

        Parameters
        ----------
        directory: String
            - path to the data directory
        fileName: String
            - name for the txt file containing the list
            - like 'filename.txt'
        withEdgeMaps: Boolean
            - True, if it shall be a trainingList
            - False, if it shall be a testList (no EdgeMaps)
    '''
    filenames = glob.glob(directory + '*.tif')
    skip = len(directory)
    text_file = open(directory + fileName, "w")
    for file in filenames:
        # generated edge maps are skipped
        if DOM_EXTENT in file or EDGES_EXTENT in file:
            continue

        text_file.write(file[skip:])
        text_file.write(' ' + file[skip:-4] + DOM_EXTENT + '.png')
        if withEdgeMaps:
            text_file.write(' ' + file[skip:-4] + EDGES_EXTENT + '.tif')
        text_file.write('\n')

    text_file.close()


def produceImagesLists4SmallerImages():
    p = Params.DOP_PATH + Params.SMALL_DOP_TRAIN
    produceImageList(directory=p, fileName='train.txt')
    produceImageList(directory=p, fileName='test.txt', withEdgeMaps=False)
    p = Params.DOP_PATH + Params.SMALL_DOP_TEST
    produceImageList(directory=p, fileName='train.txt')
    produceImageList(directory=p, fileName='test.txt', withEdgeMaps=False)


def getBefliegungsdatenSummary(path=Params.PATH_DISK):
    '''
        creates a short summary of the Befliegungsdaten in this path
    '''
    filenames = glob.glob(path + '*.info')
    data = [['# Bildflugdatum'], ['# Kamera'], ['# Scanaufloesung'],
            ['# Bezugssystem'], ['# Bemerkungen']]
    for f in filenames:
        print(f)
        # file = open(f, 'r')
        file = codecs.open(f, "r", encoding='utf-8', errors='ignore')
        text = file.readlines()
        if text[8] not in data[0]:
            data[0].append(text[8])
        if text[10] not in data[1]:
            data[1].append(text[10])
        if text[16] not in data[2]:
            data[2].append(text[16])
        if text[22] not in data[3]:
            data[3].append(text[22])
        i = 29
        while ('Copyright-Vermerk' not in text[i]):
            if text[i] not in data[4]:
                data[4].append(text[i])
            i += 1

    # save infos
    filename = path + 'summary.info'
    text_file = open(filename, "w")
    for row in data:
        for value in row:
            text_file.write(str(value))
        text_file.write('\n')
    text_file.close()


def getImageColorMeans(path=Params.PATH_DISK):
    '''
        reads every .tif image in this path (not recursive) and get the mean
        of all rgb values
    '''
    filenames = glob.glob(path + '*.tif')
    number = len(filenames)
    means = [0, 0, 0]
    for i, f in enumerate(filenames):
        if EDGES_EXTENT in f:
            continue
        image = np.array(openImageFile(f))
        m = np.mean(image, axis=(0, 1))
        means += m
        if i % 100 == 0:
            print(i, '/', number, '|', m)
    for i in range(len(means)):
        means[i] = means[i] / number
    return means


def saveBigImagesSeperately(path=Params.DOP_PATH + Params.BIG_DOP_TRAIN):
    files = glob.glob(path + '*.tif')
    imageName = re.compile(r'(dop20.*).tif')
    saveDir = path + 'bilder/'
    for f in files:
        image = openImageFile(f)
        # maximum size for python to work on
        image = image[:9440, :9440]
        imageName = re.compile(r'(dop20.*).tif')
        mo = imageName.search(f).group(1)
        newFilename = saveDir + mo

        imsave(newFilename, image)


if __name__ == "__main__":
    print(timeit.timeit("saveBigImagesSeperately()", number=1,
                        setup="from __main__ import saveBigImagesSeperately"),
          'sek')
    # saveBigImagesSeperately()
