# This file is part of PyOP2
#
# PyOP2 is Copyright (c) 2012, Imperial College London and
# others. Please see the AUTHORS file in the main source directory for
# a full list of copyright holders.  All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * The name of Imperial College London or that of other
#       contributors may not be used to endorse or promote products
#       derived from this software without specific prior written
#       permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTERS
# ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDERS OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
# OF THE POSSIBILITY OF SUCH DAMAGE.

import h5py
from math import sqrt
import numpy as np
import os

from pyop2 import op2, utils


def main(opt):
    from airfoil_direct_kernels import save_soln, dummy, update

    try:
        with h5py.File(opt['mesh'], 'r') as f:

            # Declare sets, maps, datasets and global constants

            nodes = op2.Set.fromhdf5(f, "nodes")
            edges = op2.Set.fromhdf5(f, "edges")
            bedges = op2.Set.fromhdf5(f, "bedges")
            cells = op2.Set.fromhdf5(f, "cells")

            p_bound = op2.Dat.fromhdf5(bedges, f, "p_bound")
            p_x = op2.Dat.fromhdf5(nodes ** 2, f, "p_x")
            p_q = op2.Dat.fromhdf5(cells ** 4, f, "p_q")
            p_qold = op2.Dat.fromhdf5(cells ** 4, f, "p_qold")
            p_adt = op2.Dat.fromhdf5(cells, f, "p_adt")
            p_res = op2.Dat.fromhdf5(cells ** 4, f, "p_res")

            op2.Const.fromhdf5(f, "gam")
            op2.Const.fromhdf5(f, "gm1")
            op2.Const.fromhdf5(f, "cfl")
            op2.Const.fromhdf5(f, "eps")
            op2.Const.fromhdf5(f, "mach")
            op2.Const.fromhdf5(f, "alpha")
            op2.Const.fromhdf5(f, "qinf")
    except IOError:
        import sys
        print "Failed reading mesh: Could not read from %s\n" % opt['mesh']
        sys.exit(1)

    # Main time-marching loop

    niter = 1000

    for i in range(1, niter + 1):

        # Save old flow solution - DIRECT
        op2.par_loop(save_soln, cells,
                     p_q(op2.READ),
                     p_qold(op2.WRITE))

        # Predictor/corrector update loop
        for k in range(2):

            # Dummy data...
            op2.par_loop(dummy, cells,
                         p_res(op2.WRITE),
                         p_adt(op2.WRITE))

            # Update flow field - DIRECT
            rms = op2.Global(1, 0.0, np.double, "rms")
            op2.par_loop(update, cells,
                         p_qold(op2.READ),
                         p_q(op2.WRITE),
                         p_res(op2.RW),
                         p_adt(op2.READ),
                         rms(op2.INC))
        # Print iteration history
        rms = sqrt(rms.data / cells.size)
        if i % 100 == 0:
            print " %d  %10.5e " % (i, rms)

if __name__ == '__main__':
    parser = utils.parser(group=True, description="PyOP2 airfoil demo")
    parser.add_argument('-m', '--mesh', default='meshes/new_grid.h5',
                        help='HDF5 mesh file to use (default: meshes/new_grid.h5)')
    parser.add_argument('-p', '--profile', action='store_true',
                        help='Create a cProfile for the run')
    opt = vars(parser.parse_args())

    # pass arg "-b sequential_llvm" for llvm
    print "--- BACKEND: " + opt["backend"] + " ---"
    op2.init(**opt)
    main(opt)