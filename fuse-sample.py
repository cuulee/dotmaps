#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
lltest.py - Example file system for Python-LLFUSE.

This program presents a static file system containing a single file. It is
compatible with both Python 2.x and 3.x. Based on an example from Gerion Entrup.

Copyright © 2015 Nikolaus Rath <Nikolaus.org>
Copyright © 2015 Gerion Entrup.

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

from __future__ import division, print_function, absolute_import

import os
import sys

# We are running from the Python-LLFUSE source directory, put it
# into the Python path.
basedir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
if (os.path.exists(os.path.join(basedir, 'setup.py')) and
    os.path.exists(os.path.join(basedir, 'src', 'llfuse'))):
    sys.path.append(os.path.join(basedir, 'src'))

from argparse import ArgumentParser
import stat
import logging
import errno
import llfuse

from Tiler import remote

try:
    import faulthandler
except ImportError:
    pass
else:
    faulthandler.enable()

log = logging.getLogger(__name__)

dots_name = b'dots.mbtiles'
dots_node = llfuse.ROOT_INODE+1
dots_href = 'http://mike.teczno.com/img/openaddr-us-ca-dots.mbtiles'

class TestFs(llfuse.Operations):
    def __init__(self, *args, **kwargs):
        llfuse.Operations.__init__(self, *args, **kwargs)
        self.dots_file = remote.RemoteFileObject(dots_href, verbose=True, block_size=256*1024)

    def getattr(self, inode, ctx=None):
        entry = llfuse.EntryAttributes()
        if inode == llfuse.ROOT_INODE:
            entry.st_mode = (stat.S_IFDIR | 0o755)
            entry.st_size = 0
        elif inode == dots_node:
            entry.st_mode = (stat.S_IFREG | 0o644)
            entry.st_size = self.dots_file.length
        else:
            raise llfuse.FUSEError(errno.ENOENT)

        stamp = int(1438467123.985654 * 1e9)
        entry.st_atime_ns = stamp
        entry.st_ctime_ns = stamp
        entry.st_mtime_ns = stamp
        entry.st_gid = os.getgid()
        entry.st_uid = os.getuid()
        entry.st_ino = inode

        return entry

    def lookup(self, parent_inode, name, ctx=None):
        if parent_inode != llfuse.ROOT_INODE or name != dots_name:
            raise llfuse.FUSEError(errno.ENOENT)
        return self.getattr(dots_node)

    def _opendir(self, inode, ctx):
        if inode != llfuse.ROOT_INODE:
            raise llfuse.FUSEError(errno.ENOENT)
        return inode

    def _readdir(self, fh, off):
        assert fh == llfuse.ROOT_INODE

        # only one entry
        if off == 0:
            yield (dots_name, self.getattr(dots_node), 1)

    def open(self, inode, flags, ctx):
        log.debug('open: {}, {}, {}'.format(inode, flags, ctx))
        if inode != dots_node:
            raise llfuse.FUSEError(errno.ENOENT)
        if flags & os.O_RDWR or flags & os.O_WRONLY:
            raise llfuse.FUSEError(errno.EPERM)
        return inode

    def read(self, fh, off, size):
        log.debug('read: {}, {}, {}'.format(fh, off, size))
        assert fh == dots_node
        self.dots_file.seek(off)
        return self.dots_file.read(size)
    
    def release(self, inode):
        log.debug('release: {}'.format(inode))

def init_logging(debug=False):
    formatter = logging.Formatter('%(asctime)s.%(msecs)03d %(threadName)s: '
                                  '[%(name)s] %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    if debug:
        handler.setLevel(logging.DEBUG)
        root_logger.setLevel(logging.DEBUG)
    else:
        handler.setLevel(logging.INFO)
        root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

def parse_args():
    '''Parse command line'''

    parser = ArgumentParser()

    parser.add_argument('mountpoint', type=str,
                        help='Where to mount the file system')
    parser.add_argument('--debug', action='store_true', default=False,
                        help='Enable debugging output')
    parser.add_argument('--debug-fuse', action='store_true', default=False,
                        help='Enable FUSE debugging output')
    return parser.parse_args()


def main():
    options = parse_args()
    init_logging(options.debug)

    testfs = TestFs()
    fuse_options = set(llfuse.default_options)
    fuse_options.add('fsname=lltest')
    if options.debug_fuse:
        fuse_options.add('debug')
    llfuse.init(testfs, options.mountpoint, fuse_options)
    try:
        llfuse.main(workers=1)
    except:
        llfuse.close(unmount=False)
        raise

    llfuse.close()


if __name__ == '__main__':
    main()
