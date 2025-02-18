# -*- coding: utf-8 -*-
import os
import sys
import pathlib
from setuptools import find_packages, setup
from configparser import ConfigParser

# Package-wide name
cfg = ConfigParser()
cfg.read(filenames=['setup.cfg'])
VERSION = cfg.get('metadata', 'version')

# Home dir
HOME = pathlib.Path.home()

# Name with underscore (wheel filename)
PACKAGE_NAME = cfg.get('metadata', 'name')

# Name with dash (pip name, URL, S3 bucket)
PACKAGE_NAME_DASH = PACKAGE_NAME.replace('_', '-')

# Append package dir to sys.path
PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__))))
sys.path.append(os.path.abspath(os.path.join(PROJECT_DIR, "src", PACKAGE_NAME)))

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text(encoding='utf8')

# Add possible dependencies here
DEPENDENCIES = ["pathlib"]

# Github download link
GITHUB_URL = "https://github.com/yuchdev/{PACKAGE_NAME}"

# Wheel filename, e.g. package_name-1.0.0-py3-none-any.whl
WHEEL_FILE = f"{PACKAGE_NAME}-{VERSION}-py3-none-any.whl"

# Tarball filename, e.g. package_name-1.0.0.tar.gz
TARGET_TARBALL = f"{PACKAGE_NAME}-{VERSION}.tar.gz"

# Github download link
GITHUB_DOWNLOAD = f"{GITHUB_URL}/releases/download/release.{VERSION}/{TARGET_TARBALL}"

# AWS download link
AWS_DOWNLOAD = f"https://{PACKAGE_NAME_DASH}.s3.us-east-1.amazonaws.com/packages/{WHEEL_FILE}"

# PyPI project page
PYPI_URL = f"https://pypi.org/project/{PACKAGE_NAME_DASH}/"

# Issue tracker
ISSUE_TRACKER = "{github_url}/issues".format(github_url=GITHUB_URL)

setup(
    name=PACKAGE_NAME,
    version=VERSION,
    author="Yurii Cherkasov",
    author_email="strategarius@protonmail.com",
    description="Scrap requested book information from Amazon, Leanpub and some other shops.",
    long_description=README,
    long_description_content_type="text/markdown",
    url=GITHUB_URL,
    download_url=GITHUB_DOWNLOAD,
    project_urls={
        "Bug Tracker": ISSUE_TRACKER,
    },
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Science/Research",

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate you support Python 3. These classifiers are *not*
        # checked by 'pip install'. See instead 'python_requires' below.
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(where=str(HERE / 'src')),
    package_dir={"": "src"},
    package_data={PACKAGE_NAME: ['defaults/*']},
    python_requires=">=3.8",
    install_requires=DEPENDENCIES,
)
