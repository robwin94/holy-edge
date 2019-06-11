import glob
import timeit
import ImageHandling as ih
import GeometryConvertion as gc
import Params
from shutil import copyfile
import numpy as np
import re


def getEdgeMapsForTiffiles(path=Params.DOP_PATH):
    filenames = glob.glob(path + '*.tif')
    print(len(filenames))
    for file in filenames:
        # generated edge maps are skipped
        if ih.EDGES_EXTENT in file:
            continue
        # print(file)
        bbox = gc.getBBoxForTifFile(file)
        gc.bbox2EdgeMap(bbox, file[:-4], True)

    print('produced EdgeFiles\n')
#    ih.produceImageList(path, 'train_list.txt')
#    print('prduced ImageList\n')


def big2smallWithEdgeMaps(path=Params.DOP_PATH, train=False, test=True):
    if train:
        ih.makeSmallerImages(path + Params.BIG_DOP_TRAIN)
        ih.produceImageList(directory=path + Params.SMALL_DOP_TRAIN,
                            fileName='train.txt')
    if test:
        ih.makeSmallerImages(path + Params.BIG_DOP_TEST, dirTo=path
                             + Params.SMALL_DOP_TEST, forTraining=False)
        ih.produceImageList(directory=path + Params.SMALL_DOP_TEST,
                            fileName='test.txt', withEdgeMaps=False)


def big2small4secondNet(path=Params.DOP_PATH):
    ih.makeSmallerImages(path + Params.BIG_DOP_TEST, dirTo=path
                         + Params.SMALL_DOP_TEST, for2ndNet=True)


def chooseRandomBigImages(pathFrom=Params.PATH_DISK, pathTo=Params.DOP_PATH +
                          'images/'):
    filenames = glob.glob(pathFrom + '*.tif')
    imageName = re.compile(r'(dop20.*tif)')
    filenames = np.random.choice(filenames, 30)
    for f in filenames:
        mo = imageName.search(f)
        to = pathTo + mo.group(1)
        copyfile(f, to)
        copyfile(f[:-3] + 'tfw', to[:-3] + 'tfw')


def getDOM4Images(file):
    return


def main():
    big2small4secondNet()


if __name__ == "__main__":
    #    print(timeit.timeit("main()", number=1,
    #               setup="from __main__ import big2smallWithEdgeMaps"),
    #          'sek')
    main()
