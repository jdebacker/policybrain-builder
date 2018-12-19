"""
Policy Simulaton Library (PSL) model Anaconda-Cloud package release logic.
"""
# CODING-STYLE CHECKS:
# pycodestyle release.py
# pylint --disable=locally-disabled release.py

import os
import re
import time
import shutil
import pkgbld.utils as u


BASE_PYTHON_VERSIONS = ['3.6']
OS_PLATFORMS = ['osx-64', 'linux-64', 'win-32', 'win-64']

GITHUB_URL = 'https://github.com/PSLmodels'
ANACONDA_USER = 'pslmodels'
ANACONDA_CHANNEL = ANACONDA_USER
HOME_DIR = os.path.expanduser('~')
ANACONDA_TOKEN_FILE = os.path.join(
    HOME_DIR,
    '.{}_anaconda_token'.format(ANACONDA_USER)
)
WORKING_DIR = os.path.join(
    HOME_DIR,
    'temporary_pkgbld_working_dir'
)
BUILDS_DIR = 'pkgbld_output'


def release(repo_name, pkg_name, version, also37=True, dryrun=False):
    """
    Conduct local build and upload to Anaconda Cloud of conda packages
    for each operating-system platform and Python version for the specified
    Policy Simulation Library (PSL) model and version.

    Parameters
    ----------
    repo_name: string
        model repository name appended to GITHUB_URL

    pkg_name: string
        model package name for repository specified by repo_name

    version: string
        model version string having X.Y.Z semantic-versioning pattern;
        must be a release tag in the model repository

    also37: boolean
        whether or not packages are built/uploaded for Python 3.7

    dryrun: boolean
        whether or not just the package build/upload plan is shown

    Raises
    ------
    ValueError:
        if parameters are not valid
        if ANACONDA_TOKEN_FILE does not exist

    Returns
    -------
    Nothing

    Notes
    -----
    Example usage: release('Tax-Calculator', 'taxcalc', '0.22.2')
    """
    # pylint: disable=too-many-statements,too-many-locals,too-many-branches

    # check parameters
    if not isinstance(repo_name, str):
        raise ValueError('repo_name is not a string object')
    if not isinstance(pkg_name, str):
        raise ValueError('pkg_name is not a string object')
    if not isinstance(version, str):
        raise ValueError('version is not a string object')
    if not isinstance(also37, bool):
        raise ValueError('also37 is not a boolean object')
    if not isinstance(dryrun, bool):
        raise ValueError('dryrun is not a boolean object')
    pattern = r'^[0-9]+\.[0-9]+\.[0-9]+$'
    if re.match(pattern, version) is None:
        msg = 'version={} does not have X.Y.Z semantic-versioning pattern'
        raise ValueError(msg.format(version))

    # check for token file
    if not os.path.isfile(ANACONDA_TOKEN_FILE):
        msg = 'Anaconda token file {} does not exist'
        raise ValueError(msg.format(ANACONDA_TOKEN_FILE))

    # specify Python versions
    if also37:
        python_versions = BASE_PYTHON_VERSIONS + ['3.7']
    else:
        python_versions = BASE_PYTHON_VERSIONS

    # show build/upload plan
    print(': Package-Builder will build model packages for:')
    print(':   repository_name = {}'.format(repo_name))
    print(':   package_name = {}'.format(pkg_name))
    print(':   model_version = {}'.format(version))
    print(':   python_versions = {}'.format(python_versions))
    print(': Package-Builder will upload model packages to:')
    print(':   Anaconda channel = {}'.format(ANACONDA_CHANNEL))
    print(':   using token in file = {}'.format(ANACONDA_TOKEN_FILE))
    if dryrun:
        print(': Package-Builder is quitting')
        return

    # show date and time
    print((': Package-Builder is starting at {}'.format(time.asctime())))

    # make empty working directory
    if os.path.isdir(WORKING_DIR):
        shutil.rmtree(WORKING_DIR)
    os.mkdir(WORKING_DIR)
    os.chdir(WORKING_DIR)

    # clone code for model_version from model repository
    print((': Package-Builder is cloning repository code '
           'for {}'.format(version)))
    cmd = 'git clone --branch {} --depth 1 {}/{}/'.format(
        version, GITHUB_URL, repo_name
    )
    u.os_call(cmd)
    os.chdir(repo_name)

    # specify version in several repository files
    print(': Package-Builder is setting version')
    # ... specify version in meta.yaml file
    u.file_revision(
        filename=os.path.join('conda.recipe', 'meta.yaml'),
        pattern=r'version: .*',
        replacement='version: {}'.format(version)
    )
    # ... specify version in setup.py file
    u.file_revision(
        filename='setup.py',
        pattern=r'version = .*',
        replacement='version = "{}"'.format(version)
    )
    # ... specify version in package_name/__init__.py file
    u.file_revision(
        filename=os.path.join(pkg_name, '__init__.py'),
        pattern=r'__version__ = .*',
        replacement='__version__ = "{}"'.format(version)
    )

    # build and upload model package for each Python version and OS platform
    local_platform = u.conda_platform_name()
    for pyver in python_versions:
        # ... build for local_platform
        print((': Package-Builder is building package '
               'for Python {}').format(pyver))
        cmd = ('conda build --python {} --old-build-string '
               '--channel {} --override-channels '
               '--no-anaconda-upload --output-folder {} '
               'conda.recipe').format(pyver, ANACONDA_CHANNEL, BUILDS_DIR)
        u.os_call(cmd)
        # ... convert local build to other OS_PLATFORMS
        print((': Package-Builder is converting package '
               'for Python {}').format(pyver))
        pyver_parts = pyver.split('.')
        pystr = pyver_parts[0] + pyver_parts[1]
        pkgfile = '{}-{}-py{}_0.tar.bz2'.format(pkg_name, version, pystr)
        pkgpath = os.path.join(BUILDS_DIR, local_platform, pkgfile)
        for platform in OS_PLATFORMS:
            if platform == local_platform:
                continue
            cmd = 'conda convert -p {} -o {} {}'.format(
                platform, BUILDS_DIR, pkgpath
            )
            u.os_call(cmd)
        # ... upload to Anaconda Cloud
        print((': Package-Builder is uploading packages '
               'for Python {}').format(pyver))
        for platform in OS_PLATFORMS:
            pkgpath = os.path.join(BUILDS_DIR, platform, pkgfile)
            cmd = 'anaconda -t {} upload -u {} --force {}'.format(
                ANACONDA_TOKEN_FILE, ANACONDA_USER, pkgpath
            )
            u.os_call(cmd)

    print(': Package-Builder is cleaning-up')

    # remove local packages made during this process
    cmd = 'conda build purge'
    u.os_call(cmd)

    # remove working directory and its contents
    os.chdir(HOME_DIR)
    shutil.rmtree(WORKING_DIR)

    print(': Package-Builder is finishing at {}'.format(time.asctime()))
