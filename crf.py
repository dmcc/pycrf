#!/usr/bin/env python
#
# CRF goodness
# oct 19 2006
#
# (c) 2006, david mcclosky & chris erway

from tempfile import NamedTemporaryFile
import itertools
import os

def escaper(token):
    if token == ' ':
        return 'space'
    elif token == '\n':
        return 'newline'
    elif token == '\t':
        return 'tab'
    else:
        return repr(token)

def ident(i, idx, all_i):
    """the identity feature"""
    return i
    
class CRF:
    def __init__(self, model, features, template=None):
        self.model = model
        self.features = features[:]
        self.features.insert(0, ident)
        self.template = template or []
        self.templatef = self.make_template()

    def make_template(self):
        templatef = NamedTemporaryFile()
        for idx, f in enumerate(self.features):
            print >>templatef, "U%d:%%x[0,%d]" % (idx, idx)

        for idx, t in enumerate(self.template):
            # templates are (func, pos_idx)
            # composite templates: [(f1, p1), (f2, p2), ...]
            try:
                t[0][0]
            except TypeError:
                t = (t,)
            print >>templatef, "Ut%d:" % idx + \
                  "/".join(["%%x[%d,%d]" % (pi, self.features.index(func))
                                for func,pi in t])
        templatef.flush()
        return templatef

    def make_feature_input_file(self, sequences, training=False):
        """This makes a file suitable for training or testing as input
        to CRF++.  The file has each token on its own line with all
        the features of that token.  The input is a list of sequences.
        If training=True, each item in the sequence is a (input, output)
        pair, otherwise, each item is simply an input."""
        featureinputf = NamedTemporaryFile()
        for sequence in sequences:
            if training:
                all_i = [x[0] for x in sequence]
            else:
                all_i = sequence[:]
            for idx, item in enumerate(sequence):
                if training:
                    item, output = item
                fvalues = [escaper(f(item, idx, all_i)) for f in self.features]
                if training:
                    fvalues.append(output)
                print >>featureinputf, " ".join(fvalues)
            print >>featureinputf # separate sequences by newline
        featureinputf.flush()
        return featureinputf

    def train(self, training_data):
        """training_data is a list of sequences of input and output pairs:
        ((token1, label1), ...)"""
        trainf = self.make_feature_input_file(training_data, training=True)
        # run CRF++
        os.system("crf_learn -t -p 2 %s %s %s" % (self.templatef.name,
                                                  trainf.name, self.model))

    def label(self, test_data, labels_only=True):
        """test_data is a list of sequences of input tokens (no output
        tokens): (token1, token2, ...).  If labels_only is True, the
        output is of the form (label1, label2, ...).  Otherwise, the
        output is of the form ((token1, label1), (token2, label2), ...)"""
        import commands
        dataf = self.make_feature_input_file(test_data, training=False)
        output = commands.getoutput("crf_test -m %s %s" % (self.model,
                                                           dataf.name))

        sequence = []
        for line in output.splitlines():
            if line.strip():
                pieces = line.split('\t')
                if labels_only:
                    sequence.append(pieces[-1])
                else:
                    sequence.append((pieces[0], pieces[-1]))
            else:
                yield sequence
                sequence = []
        if sequence:
            yield sequence

    def evaluate(self, data):
        """data is of the same form as train(): a list of sequences of
        input and output pairs: ((token1, label1), ...)"""
        # make tees data so we can iterate over it separately
        data1, data2 = itertools.tee(data)
        def inputgen():
            for sequence in data1:
                yield [item[0] for item in sequence]
        def goldgen():
            for sequence in data2:
                yield [item[1] for item in sequence]
        labels = self.label(inputgen(), labels_only=False)
        for labelseq, goldseq in itertools.izip(labels, goldgen()):
            yield [(i, o, gold) for (i, o), gold in zip(labelseq, goldseq)]

    def basic_accuracy(self, evaled_seqs):
        """evaled_seqs should be like output from evaluate(): a list of
        sequences, where each sequence is
        [(token1, label1, goldlabel1), (token2, label2, goldlabel2), ...]"""
        total = 0
        right = 0
        seq_total = 0
        seq_right = 0
        for sequence in evaled_seqs:
            cur_seq_right = True
            for inputtoken, outputlabel, goldlabel in sequence:
                if outputlabel == goldlabel:
                    right += 1
                else:
                    cur_seq_right = False
                total += 1
            seq_total += 1
            if cur_seq_right:
                seq_right += 1
        return right, total, seq_right, seq_total

if __name__ == '__main__':
    import optparse, sys
    crf_base = "/home/dmcc/CRF++-0.44/"

    chunkfile = crf_base + "example/chunking/train.data"
    def seqify(filename):
        sequences = []
        cur_seq = []
        for line in file(filename):
            line = line.strip()
            if line:
                cur_seq.append(line.split())
            else:
                sequences.append(cur_seq)
                cur_seq = []
        if cur_seq:
            sequences.append(cur_seq)
        return sequences
    sequences = seqify(chunkfile)

    def train_pos_iter():
        """Just read the training data"""
        for seq in sequences:
            for inp, tag, out in seq:
                yield tag
    pos_iter = itertools.cycle(train_pos_iter())
    def pos_tag(i, idx, all_i):
        return pos_iter.next()

    ioseq = [[(i[0], i[2]) for i in seq] for seq in sequences]
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

    c = CRF("testmodel", [pos_tag], templ)
    c.train(ioseq)
    # labels = c.label([[i[0] for i in seq] for seq in sequences])
    # for label in labels:
        # print label
    print c.basic_accuracy(c.evaluate(ioseq))

    # NOTE: We cannot actually test on chunking due to the pos_tag function
    # being faked.  We also cannot *not* fake it.
