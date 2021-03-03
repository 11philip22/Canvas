#! /usr/bin/env python
#
# Test script for Crypto.XXX
#

__revision__ = "$Id: test_chaffing.py,v 1.2 2006/07/29 02:52:51 phil Exp $"

from sancho.unittest import TestScenario, parse_args, run_scenarios
from Crypto.Protocol import Chaffing

tested_modules = [ "Crypto.Protocol.Chaffing" ]

text = """\
When in the Course of human events, it becomes necessary for one people to
dissolve the political bands which have connected them with another, and to
assume among the powers of the earth, the separate and equal station to which
the Laws of Nature and of Nature's God entitle them, a decent respect to the
opinions of mankind requires that they should declare the causes which impel
them to the separation.

We hold these truths to be self-evident, that all men are created equal, that
they are endowed by their Creator with certain unalienable Rights, that among
these are Life, Liberty, and the pursuit of Happiness. That to secure these
rights, Governments are instituted among Men, deriving their just powers from
the consent of the governed. That whenever any Form of Government becomes
destructive of these ends, it is the Right of the People to alter or to
abolish it, and to institute new Government, laying its foundation on such
principles and organizing its powers in such form, as to them shall seem most
likely to effect their Safety and Happiness.
"""

class ChaffingTest (TestScenario):

    def setup (self):
        pass

    def shutdown (self):
        pass

    def check_chaffing (self):
        "Simple tests of chaffing and winnowing"
        self.test_stmt('Chaffing.Chaff()')
        self.test_stmt('Chaffing.Chaff(0.5, 1)')
        self.test_exc('Chaffing.Chaff(factor=-1)', ValueError)
        self.test_exc('Chaffing.Chaff(blocksper=-1)', ValueError)

        data = [(1, 'data1', 'data1'), (2, 'data2', 'data2')]
        c = Chaffing.Chaff(1.0, 1)
        self.test_stmt('c.chaff(data)')
        chaff = c.chaff(data)
        self.test_val('len(chaff)', 4)

        c = Chaffing.Chaff(0.0, 1)
        chaff = c.chaff(data)
        self.test_val('len(chaff)', 2)

if __name__ == "__main__":
    (scenarios, options) = parse_args()
    run_scenarios(scenarios, options)
