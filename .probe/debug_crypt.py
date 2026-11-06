import os, sys
T = r"C:\Users\q8369\AppData\Local\Temp\dsh-fXE92q"
sys.path.insert(0, os.path.join(T, "pylibs"))
import cryptography
print("cryptography", cryptography.__version__, cryptography.__file__)
try:
    import importlib.metadata as md
    print("metadata version:", md.version("cryptography"))
except Exception as e:
    print("metadata failed:", e)
import pypdf._crypt_providers as cp
print("provider module dir:", [n for n in dir(cp) if not n.startswith('_')])
import pypdf._crypt_providers._cryptography as cc
print("cryptography provider import OK")
from pypdf._crypt_providers._fallback import _DEPENDENCY_ERROR_STR
print("dep err:", _DEPENDENCY_ERROR_STR)
