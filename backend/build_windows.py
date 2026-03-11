import os
import sys
import sysconfig
import subprocess

# 1. Safely extract Python headers and libraries (works even inside venvs)
py_include = sysconfig.get_path("include")
py_libs = os.path.join(sys.base_exec_prefix, "libs")

# 2. Direct NVCC compilation command for Windows
cmd = [
    "nvcc", "-O3", "-shared",
    "-arch=sm_89",               # RTX 40xx (Ada Lovelace). Use sm_75 for RTX 20xx, sm_86 for RTX 30xx
    "-Xcompiler", "/MD",         # Tells nvcc to link against the MSVC dynamic runtime
    f'-I{py_include}',         
    f'-L{py_libs}', 
    "cuda_solver.cu", 
    "-o", "cuda_solver.pyd"      # .pyd is the Windows equivalent of a .so Python extension
]

print("Running NVCC build command...\n")
print(" ".join(cmd) + "\n")

try:
    subprocess.run(cmd, check=True)
    print("\n✅ Successfully compiled cuda_solver.pyd!")
except subprocess.CalledProcessError:
    print("\n❌ Build failed. Check the errors above.")