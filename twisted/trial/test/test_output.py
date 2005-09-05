from twisted.trial import unittest
from twisted.trial.assertions import FailTest
from twisted.python import util
from twisted.internet import utils, reactor, interfaces
import os, re

def getTrialPath():
    fp = os.path.abspath(unittest.__file__)
    trialPath = fp.split(os.path.sep)[:-3] + ['bin', 'trial']
    return os.path.normpath(os.path.join(fp, os.pardir, os.pardir,
                                         os.pardir, 'bin', 'trial'))


if not interfaces.IReactorProcess.providedBy(reactor):
    skip = "These tests require the ability to spawn processes"
    

class TestImportErrors(unittest.TestCase):
    """Actually run trial on the command line and check that the output is
    what we expect.
    """
    ## XXX -- ideally refactor the trial top-level stuff so we don't have to
    ## shell out for this stuff.

    debug = False

    def runTrial(self, *args):
        path = self._getMockPath()
        env = os.environ.copy()
        if not env.has_key('PYTHONPATH'):
            env['PYTHONPATH'] = path
        else:
            env['PYTHONPATH'] += os.pathsep + path
        d = utils.getProcessOutput(getTrialPath(), args=args, errortoo=1,
                                   env=env)
        if self.debug:
            d.addCallback(self._print)
        return d

    def _print(self, stuff):
        print stuff
        return stuff

    def _getMockPath(self):
        from twisted.trial import test
        return os.path.normpath(util.sibpath(test.__file__, 'foo'))

    def failUnlessIn(self, container, containee, *args, **kwargs):
        # redefined to be useful in callbacks
        unittest.TestCase.failUnlessIn(self, containee, container,
                                       *args, **kwargs)
        return container

    def failIfIn(self, container, containee, *args, **kwargs):
        # redefined to be useful in callbacks
        unittest.TestCase.failIfIn(self, containee, container,
                                   *args, **kwargs)
        return container

    def test_trialFound(self):
        self.failUnless(os.path.isfile(getTrialPath()), getTrialPath())

    def test_mockPathCorrect(self):
        # This doesn't test a feature.  This tests that we are accurately finding
        # the directory with all of the mock modules and packages.
        path = self._getMockPath()
        self.failUnless(path.endswith('twisted/trial/test/foo'))
        self.failUnless(os.path.isdir(path))

    def test_trialRun(self):
        d = self.runTrial('--help')
        d.addCallback(self.failUnless, 'trial')
        return d

    def test_nonexistentModule(self):
        d = self.runTrial('twisted.doesntexist')
        d.addCallback(self.failUnlessIn, 'IMPORT ERROR')
        d.addCallback(self.failUnlessIn, 'twisted.doesntexist')
        return d

    def test_nonexistentPackage(self):
        d = self.runTrial('doesntexist')
        d.addCallback(self.failUnlessIn, 'doesntexist')
        d.addCallback(self.failUnlessIn, 'IOError')
        d.addCallback(self.failIfIn, 'IMPORT ERROR')
        return d

    def test_nonexistentPackageWithModule(self):
        d = self.runTrial('doesntexist.barney')
        d.addCallback(self.failUnlessIn, 'doesntexist.barney')
        d.addCallback(self.failUnlessIn, 'IOError')
        d.addCallback(self.failIfIn, 'IMPORT ERROR')
        return d

    def test_badpackage(self):
        d = self.runTrial('badpackage')
        d.addCallback(self.failUnlessIn, 'IMPORT ERROR')
        d.addCallback(self.failUnlessIn, 'badpackage')
        d.addCallback(self.failIfIn, 'IOError')
        return d

    def test_moduleInBadpackage(self):
        d = self.runTrial('badpackage.test_module')
        d.addCallback(self.failUnlessIn, "IMPORT ERROR")
        d.addCallback(self.failUnlessIn, "badpackage.test_module")
        d.addCallback(self.failIfIn, 'IOError')
        return d

    def test_badmodule(self):
        d = self.runTrial('package.test_bad_module')
        d.addCallback(self.failUnlessIn, 'IMPORT ERROR')
        d.addCallback(self.failUnlessIn, 'package.test_bad_module')
        d.addCallback(self.failIfIn, 'IOError')
        d.addCallback(self.failIfIn, '<module')
        return d

    def test_badimport(self):
        d = self.runTrial('package.test_import_module')
        d.addCallback(self.failUnlessIn, 'IMPORT ERROR')
        d.addCallback(self.failUnlessIn, 'package.test_import_module')
        d.addCallback(self.failIfIn, 'IOError')
        d.addCallback(self.failIfIn, '<module')
        return d

    def test_recurseImport(self):
        d = self.runTrial('-R', 'package')
        d.addCallback(self.failUnlessIn, 'IMPORT ERROR')
        d.addCallback(self.failUnlessIn, 'package.test_bad_module')
        d.addCallback(self.failUnlessIn, 'package.test_import_module')
        d.addCallback(self.failIfIn, '<module')
        d.addCallback(self.failIfIn, 'IOError')
        return d
    test_recurseImport.todo = "This is a regression, I think -- jml"

    def test_regularRun(self):
        d = self.runTrial('package.test_module')
        d.addCallback(self.failIfIn, 'IMPORT ERROR')
        d.addCallback(self.failIfIn, 'IOError')
        d.addCallback(self.failUnlessIn, 'OK')
        d.addCallback(self.failUnlessIn, 'PASSED (successes=1)')
        return d
    
    ## XXX -- needs tests for
    ## - recursive on package that contains module that doesn't import
    ## - package / modules that _do_ import