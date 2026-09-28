"""Serialization helpers for local AI-only execution."""
from __future__ import annotations
from dataclasses import asdict, is_dataclass
from pathlib import Path
import numpy as np


def to_builtin(x):
    if is_dataclass(x): return to_builtin(asdict(x))
    if isinstance(x,dict): return {str(k):to_builtin(v) for k,v in x.items()}
    if isinstance(x,(list,tuple,set)): return [to_builtin(v) for v in x]
    if isinstance(x,np.ndarray): return x.tolist()
    if isinstance(x,np.generic): return x.item()
    if isinstance(x,Path): return str(x)
    return x
