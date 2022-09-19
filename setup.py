import os
import setuptools
import sys
import platform
import codecs
from distutils.command.build_ext import build_ext

if platform.system() != 'Windows':
    readme_path = os.path.join(os.path.dirname(__file__), 'README.rst')
    with codecs.open(readme_path, encoding='utf8') as f:
        readme = f.read()
else:
    # The format is messed up with extra line breaks when building wheels on windows.
    # Skip readme in this case.
    readme = 'Persistent collections, see https://github.com/tobgu/pyrsistent/ for details.'

extensions = []
if platform.python_implementation() == 'CPython' and os.getenv('PYRSISTENT_SKIP_EXTENSION') is None:
    extensions = [
        setuptools.Extension(
            'pyrsistent_extras._psequence._c_ext',
            sources=['pyrsistent_extras/psequence/_c_ext.c']
        ),
    ]

needs_pytest = {'pytest', 'test', 'ptr'}.intersection(sys.argv)
pytest_runner = ['pytest-runner'] if needs_pytest else []


class custom_build_ext(build_ext):
    '''Allow C extension building to fail.'''

    warning_message = '''
********************************************************************************
WARNING: Could not build the %s.
         Pyrsistent will still work but performance may be degraded.
         %s
********************************************************************************
'''

    def run(self):
        try:
            build_ext.run(self)
        except Exception:
            e = sys.exc_info()[1]
            sys.stderr.write('%s\n' % str(e))
            sys.stderr.write(self.warning_message % ('extension modules', 'There was an issue with your platform configuration - see above.'))

    def build_extension(self, ext):
        name = ext.name
        try:
            build_ext.build_extension(self, ext)
        except Exception:
            e = sys.exc_info()[1]
            sys.stderr.write('%s\n' % str(e))
            sys.stderr.write(self.warning_message % ('%s extension module' % name, 'The output above this warning shows how the compilation failed.'))

setuptools.setup(
    name='pyrsistent-extras',
    description='Extra data structures for pyrsistent',
    long_description=readme,
    long_description_content_type='text/x-rst',
    author='mingmingrr',
    author_email='mingmingrr@gmail.com',
    url='http://github.com/mingmingrr/pyrsistent-extras',
    license='MIT',
    license_files=['LICENSE.mit'],
    #  py_modules=['_pyrsistent_version'],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    test_suite='tests',
    tests_require=['pytest<7', 'hypothesis<7'],
    scripts=[],
    setup_requires=pytest_runner,
    ext_modules=extensions,
    cmdclass={'build_ext': custom_build_ext},
    packages=[
        'pyrsistent_extras',
        'pyrsistent_extras._psequence',
    ],
    package_data={'pyrsistent-extras': ['py.typed']},
    python_requires='>=3.7',
)
