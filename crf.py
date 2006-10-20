#!/usr/bin/env python
#
# CRF goodness
# oct 19 2006
#
# (c) 2006, david mcclosky & chris erway

from tempfile import NamedTemporaryFile
import os

def ident(i, idx, all_i):
    """ the identity feature"""
    return i
    
class CRF:
    def __init__(self, model):
        self.model = model

    def train(self, training_data, features, template=None):
        template = template or []
        features.insert(0, ident)
        trainf = NamedTemporaryFile()
        all_i = [x[0] for x in training_data]
        # XXX handle (None,None) 
        for idx,(i,o) in enumerate(training_data):
            fvalues = [f(i,idx,all_i) for f in features]
            print >>trainf, " ".join(fvalues + [o])

        templatef = NamedTemporaryFile()
        for idx,f in enumerate(features):
            print >>templatef, "U%d:%%x[0,%d]" % (idx, idx)

        for idx,t in enumerate(template):
            # templates are (func, pos_idx)
            # composite templates: [(f1, p1), (f2, p2), ...]
            try:
                t[0][0]
            except TypeError:
                t = (t,)
            print >>templatef, "Ut%d:" % idx + \
                  "/".join(["%%x[%d,%d]" % (pi, features.index(func)) for func,pi in t])
        trainf.flush()
        templatef.flush()

        # run CRF++
        os.system("crf_learn -t -p 2 %s %s %s" % (templatef.name,
                                                  trainf.name, self.model))

    def evaluation(self, test_data):
        import commands

        commands.getoutput("crf_test -m %s %s" % (self.model, dataf))
        pass

if __name__ == '__main__':
    import optparse, sys
    c = CRF("testmodel")

    chunkfile = "/u/cce/pkg/CRF++-0.44/example/chunking/train.data"
    # this ignores newlines!! (we need to keep them for sentence delims)
    chunking = [l.split() or (None,None) for l in file(chunkfile)]

    def pos_tag(i, idx, all_i):
        return chunking[idx][1]

    ioseq = [(i[0], i[2]) for i in chunking]
    templ = [(pos_tag, x) for x in range(-2,3)]
    templ.extend( [(ident, x) for x in range(-2,3)] )

    templ.append( [(pos_tag, -2), (pos_tag, -1), (pos_tag, 0)] )
    templ.append( [(pos_tag, -1), (pos_tag, 0), (pos_tag, 1)] )
    templ.append( [(pos_tag, 0), (pos_tag, 1), (pos_tag, 2)] )

    templ.append( [(pos_tag, -2), (pos_tag, -1)] )
    templ.append( [(pos_tag, -1), (pos_tag, 0)] )
    templ.append( [(pos_tag, 0), (pos_tag, 1)] )
    templ.append( [(pos_tag, 1), (pos_tag, 2)] )

    templ.append( [(ident, -1), (ident, 0)] )
    templ.append( [(ident, 0), (ident, 1)] )

    c.train(ioseq, [pos_tag], templ)
