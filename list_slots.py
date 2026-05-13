import ctypes
from ctypes import wintypes

x = ctypes.WinDLL("XInput1_4.dll")
x.XInputGetState.argtypes = [wintypes.DWORD, ctypes.c_void_p]
x.XInputGetState.restype = wintypes.DWORD
buf = (ctypes.c_byte * 16)()
for i in range(4):
    status = "connected" if x.XInputGetState(i, buf) == 0 else "empty"
    print(f"slot {i}: {status}")
