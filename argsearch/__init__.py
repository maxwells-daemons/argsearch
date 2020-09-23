#!/usr/bin/env python3

from .interface import main
import multiprocessing

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
