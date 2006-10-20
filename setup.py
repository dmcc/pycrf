import os, sys
from distutils.command import install
from distutils.core import setup, Extension

# you need to set this to the PARSE directory of your reranking parser
parser = '/u/cce/pkg/CRF++-0.44' # edit this path
if not os.path.exists(parser):
    print "Please edit setup.py and fill in the correct parser path."
    sys.exit(1)

if len(sys.argv) < 2:
    sys.argv.extend(("build_ext", '-i'))

objs = ('encoder.o', 'feature_cache.o', 'lbfgs.o',
        'node.o', 'path.o', 'feature.o', 'feature_index.o',
        'libcrfpp.o', 'param.o', 'tagger.o')
objs = [os.path.join(parser, obj) for obj in objs]

setup(name = "pycrfpp",
      description = "Python Interface to CRF++",
      include_dirs = [parser],
      ext_modules = [
            Extension('_crfpp', 
                sources=['swig.i'],
                libraries=['stdc++'],
                extra_objects=objs)
      ]
)
