"""Small source-compatible helpers used by offline replay tooling."""
from __future__ import annotations
import numpy as np
from .features.math import normalize_rows_l2


def _concat(a,b,wa,wb):
    return normalize_rows_l2(np.c_[normalize_rows_l2(a)*np.sqrt(wa), normalize_rows_l2(b)*np.sqrt(wb)])


def named_views_from_frozen_arrays(G,Gf,L,Lf):
    gd=_concat(G,Gf,.5,.5); ld=_concat(L,Lf,.5,.5)
    return {'G_whole':G,'G_foreground':Gf,'G_dual':gd,'Gdual_Lf25':_concat(gd,Lf,.75,.25),'Gdual_Lf40':_concat(gd,Lf,.60,.40),'whole_G35_L65':_concat(G,L,.35,.65),'whole_G50_L50':_concat(G,L,.50,.50),'whole_G65_L35':_concat(G,L,.65,.35),'dual_G35_L65':_concat(gd,ld,.35,.65)}
