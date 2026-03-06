from setuptools import setup, Extension

cuda_ext = Extension(
    name='cuda_solver',
    sources=['cuda_solver.cu'],
    extra_compile_args=[
        '--compiler-options', '-fPIC',
        '-O3',
        '-arch=sm_75',  # change to match your GPU
    ],
    libraries=['cudart'],
    library_dirs=['/usr/local/cuda/lib64'],
    include_dirs=['/usr/local/cuda/include'],
)

setup(
    name='cuda_solver',
    version='1.0',
    ext_modules=[cuda_ext],
    build_ext_kwargs={'compiler': 'nvcc'},
)