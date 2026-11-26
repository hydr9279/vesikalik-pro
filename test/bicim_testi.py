import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from engine.imgutil import imread_any
r = imread_any(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ornek", "IMG_6630.HEIC"))
assert r.ndim == 3 and r.shape[2] == 3 and min(r.shape[:2]) > 100, r.shape
print("HEIC okundu:", r.shape)
