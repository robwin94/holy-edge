from owslib.wms import WebMapService
import ImageHandling as ih
import GeometryConvertion as gc
import glob
import numpy as np
import Params
import matplotlib.pyplot as plt


WMS_DOM = WebMapService(Params.WMS_DOM, version='1.3.0')
DOM_LAYER = 'schummerung'


def __printWMSInfos(wms):
    print('Titel:\t', wms.identification.title)
    layers = list(wms.contents)
    print('Layer:\t', str(layers))
    print('Operationen:\t', str([op.name for op in wms.operations]))
    print('Formate:\t', wms.getOperationByName('GetMap').formatOptions)
    print("Styles:\t", wms['schummerung'].styles)


def __getDOMFilename(imageFilename):
    return imageFilename[:-4] + Params.DOM_EXTENT + '.png'


def getDOMMap4ImageAndSaveAsPNG(file, bbox=None):
    '''
        Asks the WMS for the DOM Schummerung and saves it as a PNG

        Parameters
        ----------
        file: String
            - name of the Image file
            - used for saving also

        bbox: float[]
            - [xmin, ymin, xmax, ymax]
            - if not given, it will be found with the file name
    '''

    if bbox is None:
        bbox = gc.getBBoxForTifFile(file)
    assert len(bbox) == 4, 'Wrong length for the bbox'
    size = (Params.IMAGE_SIZE_SMALL, Params.IMAGE_SIZE_SMALL)

    img = WMS_DOM.getmap(layers=[DOM_LAYER], srs='EPSG:5650', bbox=bbox,
                         size=size, format='image/png')

    savePath = __getDOMFilename(file)
    out = open(savePath, 'wb')
    out.write(img.read())
    out.close()


def openDOMImage4ImageFile(file):
    return ih.openImageFile(__getDOMFilename(file))


def main(path=Params.DOP_PATH + Params.SMALL_DOP_TRAIN):
    # __printWMSInfos(WMS_DOM)
    filenames = glob.glob(path + '*.tif')
    print(len(filenames))
    for i, file in enumerate(filenames):
        # generated edge maps are skipped
        if ih.EDGES_EXTENT in file or Params.DOM_EXTENT in file:
            continue

        getDOMMap4ImageAndSaveAsPNG(file)

        if i % 100 == 0:
            print(i, '/', len(filenames))


def comparing_inputs(file='train.txt',
                     dirFrom=Params.DOP_PATH + Params.SMALL_DOP_TRAIN,
                     dirTo=Params.DOP_PATH + 'input-vergleich/'):
    f = open(dirFrom + file, 'r')
    text = f.readlines()
    for i, line in enumerate(text):
        files = line.split(sep=' ')
        img = ih.openImageFile(dirFrom + files[0])
        dom = ih.openImageFile(dirFrom + files[1])
        em = ih.openImageFile(dirFrom + files[2][:-1])

        a, b, c = img.shape
        fuse = np.zeros((a, 3*b, c))
        fuse[:, :b] = img / 255
        fuse[:, b:2*b] = dom / 255
        fuse[:, 2*b:] = em / 255
        fuse[:, (b, 2*b), :] = 0
        savePath = dirTo + files[0][:-4] + '_fuse.png'
        plt.imsave(savePath, fuse)
        if i == 1000:
            break


if __name__ == "__main__":
    comparing_inputs()
