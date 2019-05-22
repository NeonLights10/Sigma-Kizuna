#!/usr/bin/env python3

import os
import subprocess
import sys

def y_n(q):
    while True:
        ri = input('{} (y/n): '.format(q))
        if ri.lower() in ['yes', 'y']: return True
        elif ri.lower() in ['no', 'n']: return False

def update_deps():
    print("Attempting to update dependencies...")

    try:
        subprocess.check_call('"{}" -m pip install -U -r requirements.txt'.format(sys.executable), shell=True)
    except subprocess.CalledProcessError:
        raise OSError("Could not update dependencies. You will need to run '\"{0}\" -m pip install -U -r requirements.txt' yourself.".format(sys.executable))

def finalize():
    try:
        from musicbot.constants import VERSION
        print('The current MusicBot version is {0}.'.format(VERSION))
    except Exception:
        print('There was a problem fetching your current bot version. The installation may not have completed correctly.')

    print("Done!")

def main():
    print('Starting...')

    update_deps()
    finalize()

if __name__ == '__main__':
    main()
