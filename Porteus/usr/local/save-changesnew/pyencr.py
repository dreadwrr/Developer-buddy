#!/usr/bin/env python3

import sys
from pstsrg import encr

target=sys.argv[1] # to gpg file tgt
xdata=sys.argv[2] # data source       

encr(target, xdata)
