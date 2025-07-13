import os
import sys
import pathlib

from ham_amdc.ham_amdc import HamAMDC

sys.path.append(str(pathlib.Path(os.path.realpath(__file__)).parents[1]))

def main():
    HamAMDC()

    return 0

if __name__ == '__main__':

    main()

