"""Minimal numpy stand-in for Blender's `mathutils` (Vector/Matrix/Quaternion subset used by r6.py) so the rig maths can be
unit-tested without Blender.  TEST ONLY - inside Blender the real mathutils is used."""
import math, sys, types
import numpy as np

class Vector:
    def __init__(s, v=(0, 0, 0)): s.a = np.array(list(v), dtype=float)
    x = property(lambda s: s.a[0]); y = property(lambda s: s.a[1]); z = property(lambda s: s.a[2])
    def __getitem__(s, i): return s.a[i]
    def __iter__(s): return iter(s.a)
    def __len__(s): return len(s.a)
    def __add__(s, o): return Vector(s.a + Vector(o).a)
    def __sub__(s, o): return Vector(s.a - Vector(o).a)
    def __neg__(s): return Vector(-s.a)
    def __mul__(s, k): return Vector(s.a * k)
    __rmul__ = __mul__
    def __truediv__(s, k): return Vector(s.a / k)
    length = property(lambda s: float(np.linalg.norm(s.a)))
    def normalized(s): return Vector(s.a / np.linalg.norm(s.a))
    def normalize(s): s.a = s.a / np.linalg.norm(s.a)
    def dot(s, o): return float(s.a @ Vector(o).a)
    def cross(s, o): return Vector(np.cross(s.a, Vector(o).a))
    def __repr__(s): return 'Vector(%s)' % np.round(s.a, 4).tolist()

class Matrix:
    def __init__(s, m=None): s.m = np.array(m if m is not None else np.eye(3), dtype=float)
    def __getitem__(s, i): return s.m[i]
    def __matmul__(s, o):
        if isinstance(o, Vector): return Vector(s.m @ o.a)
        return Matrix(s.m @ o.m)
    def transposed(s): return Matrix(s.m.T)
    def to_3x3(s): return Matrix(s.m[:3, :3])
    def to_quaternion(s): return Quaternion.from_matrix(s.m[:3, :3])
    def to_matrix(s): return s

class Quaternion:
    def __init__(s, q=(1, 0, 0, 0)): s.q = np.array(list(q), dtype=float)
    @staticmethod
    def from_matrix(R):
        t = np.trace(R)
        if t > 0: S = math.sqrt(t + 1) * 2; q = [S / 4, (R[2, 1] - R[1, 2]) / S, (R[0, 2] - R[2, 0]) / S, (R[1, 0] - R[0, 1]) / S]
        elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]: S = math.sqrt(1 + R[0, 0] - R[1, 1] - R[2, 2]) * 2; q = [(R[2, 1] - R[1, 2]) / S, S / 4, (R[0, 1] + R[1, 0]) / S, (R[0, 2] + R[2, 0]) / S]
        elif R[1, 1] > R[2, 2]: S = math.sqrt(1 + R[1, 1] - R[0, 0] - R[2, 2]) * 2; q = [(R[0, 2] - R[2, 0]) / S, (R[0, 1] + R[1, 0]) / S, S / 4, (R[1, 2] + R[2, 1]) / S]
        else: S = math.sqrt(1 + R[2, 2] - R[0, 0] - R[1, 1]) * 2; q = [(R[1, 0] - R[0, 1]) / S, (R[0, 2] + R[2, 0]) / S, (R[1, 2] + R[2, 1]) / S, S / 4]
        return Quaternion(q)
    def __getitem__(s, i): return s.q[i]
    def __iter__(s): return iter(s.q)
    def dot(s, o): return float(s.q @ o.q)
    def negate(s): s.q = -s.q
    def copy(s): return Quaternion(s.q.copy())
    def to_matrix(s):
        w, x, y, z = s.q / np.linalg.norm(s.q)
        return Matrix([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])

def install():
    m = types.ModuleType('mathutils'); m.Vector = Vector; m.Matrix = Matrix; m.Quaternion = Quaternion; sys.modules['mathutils'] = m
