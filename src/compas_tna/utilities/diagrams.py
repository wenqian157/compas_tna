from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import sys

from numpy import array
from numpy import float64
from numpy import empty_like
from numpy.linalg import cond

from scipy.linalg import cho_factor
from scipy.linalg import cho_solve
from scipy.linalg import lstsq
from scipy.linalg import solve
from scipy.linalg import norm

from scipy.sparse.linalg import factorized

from compas.numerical import connectivity_matrix
from compas.numerical import normrow
from compas.numerical import chofactor
from compas.numerical import lufactorized

from compas.numerical import dof
from compas.numerical import rref
from compas.numerical import nonpivots

from compas.numerical import equilibrium_matrix


__author__     = ['Tom Van Mele', ]
__copyright__  = 'Copyright 2014, BLOCK Research Group - ETH Zurich'
__license__    = 'MIT License'
__email__      = 'vanmelet@ethz.ch'


__all__ = [
    'count_dof',
    'identify_dof',
    'parallelise',
    'parallelise_sparse',
    'parallelise_nodal',
    'rot90',
    'apply_bounds',
    'update_q_from_qind',
    'update_z',
]


EPS = 1 / sys.float_info.epsilon


def count_dof(form):
    k2i   = form.key_index()
    xyz   = form.xyz()
    fixed = form.anchors(k2i=k2i)
    free  = list(set(range(form.number_of_vertices())) - set(fixed))
    edges = [(k2i[u], k2i[v]) for u, v in form.edges_where({'is_edge': True})]
    C     = connectivity_matrix(edges)
    E     = equilibrium_matrix(C, xyz, free)
    return dof(E)


def identify_dof(form, **kwargs):
    algo  = kwargs.get('algo') or 'sympy'
    k2i   = form.key_index()
    xyz   = form.xyz()
    fixed = form.anchors(k2i=k2i)
    free  = list(set(range(form.number_of_vertices())) - set(fixed))
    edges = [(k2i[u], k2i[v]) for u, v in form.edges_where({'is_edge': True})]
    C     = connectivity_matrix(edges)
    E     = equilibrium_matrix(C, xyz, free)
    return nonpivots(rref(E, algo=algo))


def parallelise(A, B, X, known, k=1, key=None):
    unknown = list(set(range(X.shape[0])) - set(known))
    A11 = A[unknown, :][:, unknown]
    A12 = A[unknown, :][:, known]
    b = B[unknown] - A12.dot(X[known])
    if cond(A11) < EPS:
        if key:
            Y = cho_solve(chofactor(A11, key), b)
        else:
            Y = cho_solve(cho_factor(A11), b)
        X[unknown] = Y
        return X
    Y = lstsq(A11, b)
    Y = Y[0]
    X[unknown] = Y
    return X


def parallelise_sparse(A, B, X, known, k=1, key=None):
    unknown = list(set(range(X.shape[0])) - set(known))
    A11 = A[unknown, :][:, unknown]
    A12 = A[unknown, :][:, known]
    b = B[unknown] - A12.dot(X[known])
    if key:
        solve = lufactorized(A11, key)
        Y = solve(b)
    else:
        solve = factorized(A11)
        Y = solve(b)
    X[unknown] = Y
    return X


# replace these for loops
def parallelise_nodal(xy, C, targets, i_nbrs, ij_e, fixed=None, kmax=100):
    fixed = fixed or []
    fixed = set(fixed)

    n = xy.shape[0]

    for k in range(kmax):

        xy0 = xy.copy()
        uv  = C.dot(xy)
        l   = normrow(uv)

        for j in range(n):
            if j in fixed:
                continue

            nbrs     = i_nbrs[j]
            xy[j, :] = 0.0

            for i in nbrs:
                if (i, j) in ij_e:
                    e = ij_e[(i, j)]
                    t = targets[e]
                else:
                    e = ij_e[(j, i)]
                    t = -targets[e]

                xy[j] += xy0[i] + l[e, 0] * t

            xy[j] /= len(nbrs)


# move to AGS?
def rot90(xy, zdir=1.0):
    temp = empty_like(xy)
    temp[:, 0] = - zdir * xy[:, 1]
    temp[:, 1] = + zdir * xy[:, 0]
    return temp


# move to AGS?
def apply_bounds(x, xmin, xmax):
    xsmall    = x < xmin
    xbig      = x > xmax
    x[xsmall] = xmin[xsmall]
    x[xbig]   = xmax[xbig]


# move to AGS?
# rename to compute_q_from_qind
def update_q_from_qind(q, E, ind, dep, m):
    qi = q[ind]
    Ei = E[:, ind]
    Ed = E[:, dep]
    if m > 0:
        Edt = Ed.transpose()
        A = Edt.dot(Ed).toarray()
        b = Edt.dot(Ei).dot(qi)
    else:
        A = Ed.toarray()
        b = Ei.dot(qi)
    if cond(A) > EPS:
        res = lstsq(-A, b)
        qd = res[0]
    else:
        qd = solve(-A, b)
    q[dep] = qd
    q[ind] = qi


# rename to compute_z
def update_z(xyz, Q, C, p, free, fixed, updateloads, tol=1e-6, kmax=100, display=True):
    Ci      = C[:, free]
    Cf      = C[:, fixed]
    Cit     = Ci.transpose()
    A       = Cit.dot(Q).dot(Ci)
    A_solve = factorized(A)
    B       = Cit.dot(Q).dot(Cf)
    for k in range(kmax):
        if display:
            print(k)
        updateloads(p, xyz)
        b            = p[free, 2] - B.dot(xyz[fixed, 2])
        z0           = xyz[free, 2].copy()
        xyz[free, 2] = A_solve(b)
        res          = norm(xyz[free, 2] - z0)
        if res < tol:
            break
    return res


# ==============================================================================
# Main
# ==============================================================================

if __name__ == '__main__':
    pass
