#! /usr/bin/env python

import sys
import os
libdir = os.path.join(os.path.dirname(__file__), 'lib')
sys.path.insert(0, libdir)

import main
main.main()
