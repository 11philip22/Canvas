#! /usr/bin/env python
#
# Test script for Crypto.Util.randpool.
#

__revision__ = "$Id: test_hashes.py,v 1.2 2006/07/29 02:52:51 phil Exp $"

import time, string, binascii
from sancho.unittest import TestScenario, parse_args, run_scenarios

from Crypto.Hash import *
import testdata

tested_modules = [ "Crypto.Hash.MD2", "Crypto.Hash.MD4", "Crypto.Hash.MD5",
                   "Crypto.Hash.RIPEMD", "Crypto.Hash.SHA"]

class HashTest (TestScenario):

    def setup (self):
        teststr='1'                             # Build 128K of test data
        for i in xrange(0, 17):
            teststr=teststr+teststr
        self.str_128k = teststr

    def shutdown (self):
        del self.str_128k

    def compare(self, hash_mod, strg, hex_result):
        result = binascii.a2b_hex(hex_result)
        obj = hash_mod.new(strg)
        s1 = obj.digest()

        # Check that the right hash result is produced
        self.test_val('s1', result)

        # Check that .hexdigest() produces the same output
        self.test_val('obj.hexdigest()', hex_result)

        # Test second hashing, and copying of a hashing object
        self.test_val('obj.digest()', result)
        self.test_val('obj.copy().digest()', result)


    def run_test_suite (self, hash_mod, test_vectors):
        for text, digest in test_vectors:
            self.compare(hash_mod, text, digest)

    def benchmark (self, hash_mod):
        obj = hash_mod.new()
        start=time.time()
        s=obj.update(self.str_128k)
        end=time.time()
        print hash_mod.__name__, ':', 128/(end-start), 'K/sec'

    def check_md2 (self):
        "MD2 module"
        self.run_test_suite(MD2, testdata.md2)
        self.benchmark(MD2)

    def check_md4 (self):
        "MD4 module"
        self.run_test_suite(MD4, testdata.md4)
        self.benchmark(MD4)

    def check_md5 (self):
        "MD5 module"
        self.run_test_suite(MD5, testdata.md5)
        self.benchmark(MD5)

    def check_ripemd (self):
        "RIPEMD module"
        self.run_test_suite(RIPEMD, testdata.ripemd)
        self.benchmark(RIPEMD)

    def check_sha (self):
        "SHA module"
        self.run_test_suite(SHA, testdata.sha)
        self.benchmark(SHA)

# class HashTest


if __name__ == "__main__":
    (scenarios, options) = parse_args()
    run_scenarios(scenarios, options)
