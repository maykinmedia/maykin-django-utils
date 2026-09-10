=========
Changelog
=========

0.21.0 (2026-09-10)
===================

**💥 Breaking changes**

* Migrated the PDF URL fetcher to WeasyPrint's class-based ``URLFetcher`` API,
  since WeasyPrint 70.0 removed the deprecated ``default_url_fetcher``.
  Custom fetchers should now override ``fetch()`` instead of ``__call__()``, and
  consumers of the old dict-shaped fetch result should switch to
  ``URLFetcherResponse``. The ``pdf`` extra now requires ``weasyprint>=68.0``.

**Bugfixes**

* Fixed OpenTelemetry not being initialized when uWSGI runs with ``--lazy-apps``.

**Project maintenance**

* Addressed linter errors after upgrading Ruff.
* Configured Dependabot to also monitor GitHub Actions.

0.20.1 (2026-07-13)
===================

**Bugfixes**

* Limited the ``/_healthz/`` endpoint to the Cache, Database, and Storage checks
  to avoid false failures in certain deployment environments.
* Fixed an invalid anchor rel attribute value by changing ``nofollower`` to ``nofollow``.

0.20.0 (2026-06-29)
===================

Feature release.

**💥 Breaking changes**

* The version template used in the footer has been updated to no longer load the
  ``version.css`` styles (which have been moved into ``maykin_footer.css``).

  The recommended pattern now is to add this snippet to your
  ``templates/admin/base_site.html`` template:

  .. code-block:: django

      {# Django 5.2 puts this block inside the <footer id="footer"> element #}
      {% block footer %}
          {% include "maykin_common/includes/footer.html" with user=user only %}
      {% endblock %}

  Which will include the branding and version information under the relevant conditions.

* The environment information CSS has moved from ``maykin_common/css/version.css`` to
  ``maykin_common/css/env-info.css``.

**New features**

* [#77] You can now display product branding in the admin footer.

**Project maintenance**

* Fixed some import paths in code samples in the documentation.

0.19.1 (2026-06-23)
===================

Bugfix release.

* Fixed envvar documentation generation to output bullet lists.
* Fixed crash due to wrong ``User`` base class assertion being used.
* Fixed typing/import linting setup and bug in test case.

0.19.0 (2026-05-20)
===================

Feature release.

**💥 Breaking changes**

* Dropped support for Django 4.2.

**New features**

* Confirmed support for Django 6.0.
* Added custom django-yubin email backend for projects without Celery.
* Added sphinx directives to generate envvar documentation from the ``config`` helper.
* [#18] Ported the user account privilege escalation protections in the admin from
  default project.

**Project maintenance**

* Dropped the (testing) chardet dependency.
* Removed references to the ``coverage`` extra which no longer exists and was tripping
  up tox.
* Suppressed an upstream type error that trips Pyright.
* Skip some yubin-related failing tests on Django 6.0+, see #74 for progress.
* Improved supply chain security in our Github Actions usage, added Zizmor.

0.18.0 (2026-02-12)
===================

Maintenance release.

**💥 Breaking changes**

There are some breaking changes in the health checks due to upstream changes in
django-health-check. See the `4.x migration guide <https://codingjoe.dev/django-health-check/migrate-to-v4/>`_
for details. Note that version 3.21+ provides the new APIs already.

* The ``HEALTH_CHECK`` setting is obsolete, remove it from your project.
* ``maykin_common.health_checks.default_health_check_subsets`` is removed. Remove the
  import in your project.
* Upstream refactored the DB health check and the test model is gone. Drop the
  ``health_check_db_testmodel`` table in your project.
* django-health-check 3.21+ is now required.

**New features**

* Added support for django-health-check 3.21+ and the upcoming v4+.

**Bugfixes**

* [#65] Fixed crash in OTel library instrumentation when celery/billiard aren't
  installed in the environment.

0.17.0 (2026-01-27)
===================

Feature release with minor security improvements.

**New features**

* PDF rendering with Weasyprint now (by default) only accepts the ``http(s)`` and
  ``data`` URL schemes.
* [#20] The VCR test mixin now filters out the ``Authorization`` and ``X-API-Key``
  request headers by default.

**Bugfixes**

* Fixed confusing error being raised in ``config(..., default="", split=True)``.

0.16.0 (2026-01-26)
===================

Feature release.

*This release accidentally got released as 0.15.1 too - it contains the same code*

**New features**

* [#48] Added health check tooling for Celery Worker.

**Bugfixes**

* [#56] Fixed a regression ``config`` function, where a ``default=[], split=True``
  was interpreted as having no default.

0.15.1 (2026-01-26)
===================

(Incorrect) patch release.

*This release accidentally includes the features from 0.16.0*.

* Fix a regression ``config`` function, where a ``default=[], split=True``
  was interpreted as having no default.

0.15.0 (2026-01-23)
===================

Feature release.

* Instrumented PostgreSQL, redis, celery and requests with Open Telemetry tracing.
* Improved type annotations for ``config`` function.

0.14.0 (2026-01-13)
===================

Feature release.

* [#48] Added health check tooling for Celery Beat.

0.13.0 (2026-01-09)
===================

Feature release.

* [#42] Added Dutch translation assets.
* Added ``maykin_common.health_checks`` package and ``health-checks`` extra with
  defaults for container health checks.
* Added a CLI ``maykin-common`` which knows how to execute the health checks.

0.12.0 (2026-01-05)
===================

Feature release.

* Ported the ``config`` helper for settings from default project - it's available from
  the ``maykin_common.config`` module.

0.11.0 (2025-10-08)
===================

Feature release.

.. warning::
    Please review the installation guide, as some new (custom) settings should be
    defined and new entries in the ``urlpatterns`` are expected.

* Improved the base blocks and templates for API projects (see :ref:`apis`).
* Moved the common views from default project:

    * ``PasswordResetView`` with built-in throttling support.
    * Custom ``csrf_failure`` view to handle double-click login issues.

0.10.0 (2025-09-09)
===================

Feature release.

* Add testing utility ``MetricsAssertMixin`` that provides assertions for validating
  metrics in tests (see :ref:`test-mixins-reference`)

0.9.1 (2025-09-05)
==================

Bugfix release.

* Fixed image data in HTML to PDF rendering being parsed as a URL.

0.9.0 (2025-08-27)
==================

Feature release.

* [#6] Fixed missing test coverage for migration operations.
* Added API ``index_component`` template.
* Added Maykin logo/favicon static assets.
* Added template block for header in ``index_base.html``.

0.8.0 (2025-08-21)
==================

Feature release for better OTel support with Celery.

* You can now defer the open telemetry setup with the ``_OTEL_DEFER_SETUP=True`` envvar.
* When using Celery process pool workers (the default), the OTel setup now automatically
  runs after the worker process has forked.

0.7.0 (2025-08-05)
==================

Feature release for Open Telemetry support.

* Added ``otel`` package extra and ``maykin_common.otel.setup_otel`` helper to
  instrument projects with Open Telemetry. See the documentation for details.
* Added test coverage for the throttling mixin and refactored it a bit.
* Fixed a reference to a stylesheet that no longer exists.

0.6.0 (2025-07-10)
==================

PDF utilities feature release.

* 💥 Renamed ``render_to_pdf`` to ``render_template_to_pdf``.
* Exposed helper ``render_to_pdf`` to render HTML to PDF without needing the template
  engine.
* Added ``variant`` option, defaulting to ``pdf/ua-1`` (accessible PDFs).

0.5.0 (2025-07-04)
==================

Feature release.

* Added a post-processing hook for ``URLField(default="")`` schemas generated by
  drf-spectacular, which don't pass OpenAPI linting/validation.

0.4.0 (2025-06-23)
==================

* Added ``vcr`` extra that adds VCRMixin and TestCases.

0.3.2 (2025-06-11)
==================

Small CSS bugfix.

* Fixed the appearance of tab titles (larger font-size and line height).
* Fixed the display-as-flex rule for the tab panel content when visible.

0.3.1 (2025-06-11)
==================

Fixed packaging mistake.

* Fixed missing Javascript assets in published package.

0.3.0 (2025-06-11)
==================

Feature and cleanup release.

* Restructured the documentation.
* [#6] The ``pdf`` module now has 100% test coverage.
* [#5] Ported the API project templates and static assets and made the landing page
  accessible.
* Improved the DX for running tests locally.
