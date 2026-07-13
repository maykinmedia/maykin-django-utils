Shared Django utilities
=======================

:Version: 0.20.1

|build-status| |code-quality| |ruff| |coverage| |docs|

|python-versions| |django-versions| |pypi-version|


Re-usable utilities for Maykin Django projects.

Maykin's Django projects all share a common base: `default-project`_ to provide a
consistent and recognizable structure accross projects. This library bundles some shared
utilities that are common in (most) projects but are too small/specific to warrant a
separate library.

maykin-common acts as a vehicle to quickly propagate changes and useful helpers to a
large number of projects that would otherwise all have to be updated manually and
one-by-one, a labour-intensive task.

**What's up with the name?**

A similar utility for the client side exists: https://github.com/maykinmedia/client-common
so we wanted to mimick this naming pattern. The NPM package has namespacing:
``@maykinmedia/client-common``, but this doesn't exist on PyPI, while using
``django-common`` as a PyPI package name *might* just be a bit arrogant.

So, the repository ``maykinmedia/django-common`` perfectly covers the contents and
purpose of the package, while the PyPI package keeps the imports short and focused:
``maykin_common``, while leaving room for potential future non-Django packages.

.. contents::

.. section-numbering::

Installation and usage
======================

See the documentation: https://maykin-django-common.readthedocs.io/en/latest/

Local development
=================

To install and develop the library locally, use:

.. code-block:: bash

    pip install -e .[tests,docs,release,pdf,mfa,axes,vcr]

When running management commands via ``django-admin``, make sure to add the root
directory to the python path (or use ``python -m django <command>``):

.. code-block:: bash

    export PYTHONPATH=. DJANGO_SETTINGS_MODULE=testapp.settings
    django-admin check
    # or other commands like:
    # django-admin makemessages -l nl

Run the tests with:

.. code-block:: bash

    tox

.. |build-status| image:: https://github.com/maykinmedia/django-common/actions/workflows/ci.yml/badge.svg
    :alt: Build status
    :target: https://github.com/maykinmedia/django-common/actions?query=workflow%3A%22Run+CI%22

.. |code-quality| image:: https://github.com/maykinmedia/django-common/actions/workflows/code_quality.yml/badge.svg
     :alt: Code quality checks
     :target: https://github.com/maykinmedia/django-common/actions?query=workflow%3A%22Code+quality+checks%22

.. |ruff| image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
    :target: https://github.com/astral-sh/ruff
    :alt: Ruff

.. |coverage| image:: https://codecov.io/github/maykinmedia/django-common/graph/badge.svg?token=NXCPTBOL6N
    :target: https://codecov.io/gh/maykinmedia/django-common
    :alt: Coverage status

.. |docs| image:: https://readthedocs.org/projects/maykin-django-common/badge/?version=latest
    :target: https://maykin-django-common.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. |python-versions| image:: https://img.shields.io/pypi/pyversions/maykin-common.svg

.. |django-versions| image:: https://img.shields.io/pypi/djversions/maykin-common.svg

.. |pypi-version| image:: https://img.shields.io/pypi/v/maykin-common.svg
    :target: https://pypi.org/project/maykin-common/

.. _default-project: https://bitbucket.org/maykinmedia/default-project
