"""
Distutils convenience functionality.
"""

import sys, os, types
from distutils import sysconfig
from distutils.command import build_scripts, install_data, build_ext, build_py
from distutils.errors import CompileError
from distutils import core

twisted_subprojects = ["conch", "flow", "lore", "mail", "names",
                       "news", "pair", "runner", "web", "web2",
                       "words", "xish"]


def setup(**kw):
    if 'twisted_subproject' in kw:
        if 'twisted' not in os.listdir('.'):
            raise RuntimeError("Sorry, you need to run setup.py from the "
                               "toplevel source directory.")
        topfiles = os.path.dirname(kw['twisted_subproject'])
        tsp = os.path.normpath(os.path.join(topfiles, '..'))
        twistedpath = os.path.normpath(os.path.join(tsp, '..', '..'))
        
        kw['packages'] = getPackages(tsp, parent='twisted')
        kw['data_files'] = getDataFiles(tsp, parent=twistedpath)
        del kw['twisted_subproject']
        
    if 'cmdclass' not in kw:
        kw['cmdclass'] = {
            'install_data': install_data_twisted,
            'build_scripts': build_scripts_twisted,
            }
    if 'detectExtensions' in kw:
        if 'ext_modules' not in kw:
            kw['ext_modules'] = [True] # distutils is so lame

        dE = kw['detectExtensions']
        del kw['detectExtensions']
        class my_build_ext(build_ext_twisted):
            detectExtensions = dE
        kw.setdefault('cmdclass', {})['build_ext'] = my_build_ext
    return core.setup(**kw)


# Names that are exluded from globbing results:
EXCLUDE_NAMES = ["{arch}", "CVS", ".cvsignore", "_darcs",
                 "RCS", "SCCS", ".svn"]
EXCLUDE_PATTERNS = ["*.py[cdo]", "*.s[ol]", ".#*", "*~", "*.py"]

import glob, fnmatch

def _filterNames(names):
    """Given a list of file names, return those names that should be copied.
    """
    names = [n for n in names
             if n not in EXCLUDE_NAMES]
    # This is needed when building a distro from a working
    # copy (likely a checkout) rather than a pristine export:
    for pattern in EXCLUDE_PATTERNS:
        names = [n for n in names
                 if (not fnmatch.fnmatch(n, pattern)) and (not n.endswith('.py'))]
    return names

def relativeTo(basepath, relativee):
    """
    Gets 'relativee' relative to 'basepath'.

    i.e.,

    >>> relativeTo('/home/', '/home/radix/')
    'radix'
    >>> relativeTo('.', '/home/radix/Projects/Twisted') # curdir is /home/radix
    'Projects/Twisted'

    The 'relativee' must be a child of 'basepath'.
    """
    basepath = os.path.abspath(basepath)
    relativee = os.path.abspath(relativee)
    if relativee.startswith(basepath):
        relative = relativee[len(basepath):]
        if relative.startswith('/'):
            relative = relative[1:]
        return relative
    raise ValueError("%s is not a subpath of %s" % (relativee, basepath))


def getDataFiles(dname, ignore=None, parent=None):
    """
    Get all the data files that should be included in this distutils Project.

    'dname' should be the path to the package that you're distributing.

    'ignore' is a list of sub-packages to ignore.  This facilitates
    disparate package hierarchies.  That's a fancy way of saying that
    the 'twisted' package doesn't want to include the 'twisted.conch'
    package, so it will pass ['conch'] as the value.

    'parent' is necessary if you're distributing a subpackage like
    twisted.conch.  'dname' should point to 'twisted/conch' and 'parent'
    should point to 'twisted'.  This ensures that your data_files are
    generated correctly, only using relative paths for the first element
    of the tuple ('twisted/conch/*').
    The default 'parent' is the current working directory.
    """
    parent = parent or "."
    ignore = ignore or []
    result = []
    for directory, subdirectories, filenames in os.walk(dname):
        resultfiles = []
        for exname in EXCLUDE_NAMES:
            if exname in subdirectories:
                subdirectories.remove(exname)
        for ig in ignore:
            if ig in subdirectories:
                subdirectories.remove(ig)
        for filename in _filterNames(filenames):
            resultfiles.append(filename)
        if resultfiles:
            result.append((relativeTo(parent, directory),
                           [relativeTo(parent, os.path.join(directory, filename))
                            for filename in resultfiles]))
    return result

def getPackages(dname, pkgname=None, results=None, ignore=None, parent=None):
    parent = parent or ""
    prefix = []
    if parent:
        prefix = [parent]
    bname = os.path.basename(dname)
    ignore = ignore or []
    if bname in ignore:
        return []
    if results is None:
        results = []
    if pkgname is None:
        pkgname = []
    subfiles = os.listdir(dname)
    abssubfiles = [os.path.join(dname, x) for x in subfiles]
    if '__init__.py' in subfiles:
        results.append(prefix + pkgname + [bname])
        for subdir in filter(os.path.isdir, abssubfiles):
            getPackages(subdir, pkgname=pkgname + [bname],
                        results=results, ignore=ignore,
                        parent=parent)
    res = ['.'.join(result) for result in results]
    return res

# Apple distributes a nasty version of Python 2.2 w/ all release builds of
# OS X 10.2 and OS X Server 10.2
BROKEN_CONFIG = '2.2 (#1, 07/14/02, 23:25:09) \n[GCC Apple cpp-precomp 6.14]'
if sys.platform == 'darwin' and sys.version == BROKEN_CONFIG:
    # change this to 1 if you have some need to compile
    # with -flat_namespace as opposed to -bundle_loader
    FLAT_NAMESPACE = 0
    BROKEN_ARCH = '-arch i386'
    BROKEN_NAMESPACE = '-flat_namespace -undefined_suppress'
    sysconfig.get_config_vars()
    x = sysconfig._config_vars['LDSHARED']
    y = x.replace(BROKEN_ARCH, '')
    if not FLAT_NAMESPACE:
        e = os.path.realpath(sys.executable)
        y = y.replace(BROKEN_NAMESPACE, '-bundle_loader ' + e)
    if y != x:
        print "Fixing some of Apple's compiler flag mistakes..."
        sysconfig._config_vars['LDSHARED'] = y

## Helpers and distutil tweaks

class build_scripts_twisted(build_scripts.build_scripts):
    """Renames scripts so they end with '.py' on Windows."""

    def run(self):
        build_scripts.build_scripts.run(self)
        if not os.name == "nt":
            return
        for f in os.listdir(self.build_dir):
            fpath=os.path.join(self.build_dir, f)
            if not fpath.endswith(".py"):
                try:
                    os.unlink(fpath + ".py")
                except EnvironmentError, e:
                    if e.args[1]=='No such file or directory':
                        pass
                os.rename(fpath, fpath + ".py")


class install_data_twisted(install_data.install_data):
    """I make sure data files are installed in the package directory."""
    def finalize_options(self):
        self.set_undefined_options('install',
            ('install_lib', 'install_dir')
        )
        install_data.install_data.finalize_options(self)

class build_ext_twisted(build_ext.build_ext):
    """
    Allow subclasses to easily detect and customize Extensions to
    build at install-time.
    """
    def build_extensions(self):
        """
        Override the build_ext build_extensions method to call our
        module detection function before it tries to build the extensions.
        """
        # always define WIN32 under Windows
        if os.name == 'nt':
            self.define_macros = [("WIN32", 1)]
        else:
            self.define_macros = []

        self.extensions = self.detectExtensions() or []
        build_ext.build_ext.build_extensions(self)

    def _remove_conftest(self):
        for filename in ("conftest.c", "conftest.o", "conftest.obj"):
            try:
                os.unlink(filename)
            except EnvironmentError:
                pass

    def _compile_helper(self, content):
        conftest = open("conftest.c", "w")
        try:
            conftest.write(content)
            conftest.close()

            try:
                self.compiler.compile(["conftest.c"], output_dir='')
            except CompileError:
                return False
            return True
        finally:
            self._remove_conftest()

    def _check_header(self, header_name):
        """
        Check if the given header can be included by trying to compile a file
        that contains only an #include line.
        """
        self.compiler.announce("checking for %s ..." % header_name, 0)
        return self._compile_helper("#include <%s>\n" % header_name)
