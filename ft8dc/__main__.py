import os
import sys
import pathlib

from ft8dc.ft8dc import FT8DC

sys.path.append(str(pathlib.Path(os.path.realpath(__file__)).parents[1]))

def main():
    FT8DC()

    return 0

if __name__ == '__main__':

    main()

