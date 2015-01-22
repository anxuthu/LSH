#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on Nov 21, 2012

@author: ml249
"""
from __future__ import division

import re
import logging
from collections import defaultdict
import zlib

import numpy as np

from suckerpunch.cMinhash import minhash

_logger = logging.getLogger(__name__)


class LSH(object):
    """LSH provides a way of determining the local neighbourhood of a document.

    Locality Sensitive Hashing relies on probabilistic guarantees of hashing
    functions to produce hash collisions for similar content. The implementation
    uses min hashing to produce those collisions and allows for fast
    deduplication of data sets without having to do all pairs comparisons.

    >>> lsh = LSH()
    >>> lsh.is_duplicate('This is a simple document')
    False
    >>> long_doc = 'A much longer document that contains lots of information\
    different words. The document produces many more shingles.'
    >>> lsh.is_duplicate(long_doc)
    False
    >>> lsh.is_duplicate('Not a duplicate document.')
    False
    >>> lsh.is_duplicate('This is a simple document')
    True
    >>> long_doc = long_doc.split()
    >>> long_doc = ' '.join([long_doc[0]] + long_doc[2:])
    >>> lsh.is_duplicate(long_doc)
    True"""
    def __init__(self, num_seeds=100, bins=10, char_ngram=8, rand_seed=4905):
        self._ngram = char_ngram
        self._bins = [defaultdict(list) for _ in range(bins)]
        self._shingles = {}
        np.random.seed(rand_seed)
        self._seeds = np.array(np.random.randint(0, 10e4, num_seeds),
                               dtype=np.uint32)
        self.removed_articles = 0

    def _update(self, fingerprint, doc):
        bin_size = len(fingerprint) // len(self._bins)
        for bin, head in enumerate(range(0, len(fingerprint), bin_size)):
            bucket = fingerprint[head:head + bin_size]
            self._bins[bin][bucket.sum()].append((zlib.compress(doc, 9)))

    def _neighbours(self, fingerprint):
        bin_size = len(fingerprint) // len(self._bins)
        for bin, head in enumerate(range(0, len(fingerprint), bin_size)):
            bucket = fingerprint[head:head + bin_size]
            for n in self._bins[bin][bucket.sum()]:
                yield n

    def is_duplicate(self, article, min_similarity=0.65,
                     update=True, **kwargs):
        """Checks if a document is a duplicate of an already seen document.

        If the Jaccard similarity of two documents exceeds *min_similarity*
        those two documents are deemed to be duplicates of each other.

        The method returns a boolean indicating if the document is a
        duplicate.

        If a document is not a duplicate of anything in the cache it is added to
        the cache by default. This behaviour can be turned off with the *update*
        flag.
        """

        stripped_txt = article.replace('\n', ' ')
        stripped_txt = re.sub('[\.,;:\-\+=&*!?><\(\)]*', '', stripped_txt)
        stripped_txt = stripped_txt.lower()
        stripped_txt = stripped_txt.encode('utf8').strip()
        fingerprint = minhash(stripped_txt,
                              len(stripped_txt), self._seeds, 8)

        neighbours = self._neighbours(fingerprint)

        ngram = self._ngram
        end = len(stripped_txt) - ngram + 1
        doc_shingles = set([stripped_txt[head:head + ngram] for head in
                            range(0, end)])

        for neighbour in neighbours:
            neighbour_txt = zlib.decompress(neighbour)
            end = len(neighbour_txt) - ngram + 1
            neighbour_shingles = set([neighbour_txt[head:head + ngram]
                                      for head in range(0, end)])

            union = neighbour_shingles | doc_shingles
            intersection = neighbour_shingles & doc_shingles
            jaccard = len(intersection) / (len(union) + .0)
            if jaccard >= min_similarity:
                self.removed_articles += 1
                return True

        self._update(fingerprint, stripped_txt)
        return False

if __name__ == '__main__':
    lsh = LSH()
    lsh.is_duplicate('A much longer document that contains lots of information. The document produces many more shingles.')
    lsh.is_duplicate('A longer document that contains lots of information. The document produces many more shingles.')

    import doctest
    doctest.testmod()


