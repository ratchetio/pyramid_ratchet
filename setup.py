import os.path
from setuptools import Command, find_packages, setup

HERE = os.path.abspath(os.path.dirname(__file__))

README_PATH = os.path.join(HERE, 'README.md')
try:
    README = open(README_PATH).read()
except IOError:
    README = ''

setup(
    name='pyramid_ratchet',
    version='0.1',
    description='ratchet plugin for pyramid',
    long_description=README,
    author='brianr',
    author_email='',
    url='',
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        ],
    install_requires=[
        'pyramid>=1.2',
        'requests',
        ],
    packages=find_packages(),
    zip_safe=False,
    )







