import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

requires = [
    'colander',
    'pyes',
    'pymongo',
    'pyramid',
    'pyramid_debugtoolbar',
    'pyramid_zcml',
    'pytz',
    'thrift',
    'waitress',
    ]

setup(name='Audrey',
      version='0.0.1',
      description='Audrey',
      long_description=README + '\n\n' +  CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "License :: OSI Approved :: BSD License",
        "Development Status :: 2 - Pre-Alpha",
        ],
      author='Sam Brauer',
      author_email='sam.brauer@gmail.com',
      url='',
      keywords='web pyramid pylons mongodb mpymongo elasticsearch',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=requires,
      test_suite="audrey",
      entry_points = """\
      [paste.app_factory]
      main = audrey:main
      [pyramid.scaffold]
      audrey=audrey.scaffolds:AudreyStarterTemplate
      """,
      )

