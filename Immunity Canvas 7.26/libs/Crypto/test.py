#! /usr/bin/env python
#
# Test script for the Python Cryptography Toolkit.
#

__revision__ = "$Id: test.py,v 1.2 2006/07/29 02:52:49 phil Exp $"

import os, sys


# Add the build directory to the front of sys.path
from distutils.util import get_platform
s = "build/lib.%s-%.3s" % (get_platform(), sys.version)
s = os.path.join(os.getcwd(), s)
sys.path.insert(0, s)
s = os.path.join(os.getcwd(), 'test')
sys.path.insert(0, s)

from Crypto.Util import test

args = sys.argv[1:]
quiet = "--quiet" in args
if quiet: args.remove('--quiet')

if not quiet:
    print '\nStream Ciphers:'
    print '==============='

if args: test.TestStreamModules(args, verbose= not quiet)
else: test.TestStreamModules(verbose= not quiet)

if not quiet:
    print '\nBlock Ciphers:'
    print '=============='

if args: test.TestBlockModules(args, verbose= not quiet)
else: test.TestBlockModules(verbose= not quiet)


