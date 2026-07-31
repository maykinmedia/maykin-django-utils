"""
Utilities to read and process configuration for a project.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal, Never, assert_never, overload

from decouple import Csv, Undefined, config as _config, undefined

__all__ = ["DocumentationParams", "config"]


@dataclass(slots=True)
class DocumentationParams:
    """
    Dataclass to define the parameters for documentation generation for environment
    variables loaded via the :func:`maykin_common.config.config` helper
    """

    help_text: str = ""
    """
    The description of this environment variable.
    """
    group: str | None = None
    """
    The name of the group this environment variable belongs to.
    Defaults to "Required" or "Optional" depending on whether a ``default`` is passed.
    """
    add_to_docs: bool = True
    """
    Indicates whether this environment variable should be displayed in the
    documentation.
    """
    auto_display_default: bool = True
    """
    Indicates whether the documentation directives should display the specified
    default. Can be set to ``False`` if you want to manually specify a default.
    """


no_doc = DocumentationParams(add_to_docs=False)
"""Shorthand to not include an environment variable in generated documentation"""


@overload
def config(option: str, *, documentation: DocumentationParams | None = None) -> str: ...


# discourage passing a str default with split=True
@overload
def config[T](
    option: str,
    *,
    default: str,
    split: Literal[True],
    cast: Callable[[str], T] | Undefined = undefined,
    documentation: DocumentationParams | None = None,
) -> Never: ...


@overload
def config[T](
    option: str,
    *,
    default: Sequence[T],
    split: Literal[True],
    cast: Callable[[str], T] | Undefined = undefined,
    documentation: DocumentationParams | None = None,
) -> list[T]: ...


@overload
def config(
    option: str,
    *,
    default: Undefined = undefined,
    split: Literal[True],
    cast: Undefined = undefined,
    documentation: DocumentationParams | None = None,
) -> list[str]: ...


@overload
def config[T](
    option: str,
    *,
    default: Undefined = undefined,
    split: Literal[True],
    cast: Callable[[str], T],
    documentation: DocumentationParams | None = None,
) -> list[T]: ...


@overload
def config(
    option: str, *, default: None, documentation: DocumentationParams | None = None
) -> str | None: ...


@overload
def config[T](
    option: str,
    *,
    default: T | Undefined = undefined,
    documentation: DocumentationParams | None = None,
) -> T: ...


# because we can't express difference / negation types: object \ None
@overload
def config(
    option: str,
    *,
    default: None,
    cast: Callable,
    documentation: DocumentationParams | None = None,
) -> Never: ...


@overload
def config[T](
    option: str,
    *,
    default: str | Undefined = undefined,
    cast: Callable[[str], T],
    documentation: DocumentationParams | None = None,
) -> T: ...


def config[T](
    option: str,
    *,
    default: T | Sequence[T] | None | str | Undefined = undefined,
    split: bool = False,
    cast: Callable[[str], T] | Undefined = undefined,
    documentation: DocumentationParams | None = None,
) -> str | None | T | Sequence[T]:
    """
    Pull a config parameter from the environment.

    Read the config variable ``option``. If it's optional, use the ``default`` value.

    If not ``cast`` parameter is provided, then the ``cast`` is derived from the
    ``default`` type when a default is provided. However, when you provide a ``cast``
    parameter explicitly, you must provide any ``default`` as a string as it will be
    passed to the provided ``cast`` callback.

    Note that ``default=None`` does not mean there's no default;
    omitting the ``default`` kwarg entirely means there's no default.

    Pass ``split=True`` to split the comma-separated input into a list. If a default is
    provided, it must be a list.

    Examples::

        >>> SECRET_KEY: str = config("SECRET_KEY")
        >>> DB_NAME: str = config("DB_NAME", default="my-awesome-project")
        >>> DB_PORT: int = config("DB_PORT", default=5432")
        >>> SESSION_COOKIE_DOMAIN: str | None = config(
        ...     "SESSION_COOKIE_DOMAIN", default=None
        ... )
        >>> ALLOWED_HOSTS: list[str] = config("ALLOWED_HOSTS", split=True, default=[])
        >>> CUSTOM = config(
        ...     "CUSTOM",
        ...     default="123",
        ...     cast=lambda v: int(v) if v is not None else None,
        ... )  # typed as int | None

    The ``documentation`` parameter is available to generate documentation for
    environment variables with Sphinx directives provided by this library:

    :param documentation: See :class:`maykin_common.config.DocumentationParams`
    """

    if not documentation:
        # Instantiate the defaults
        documentation = DocumentationParams()

    if documentation.add_to_docs:
        variable = EnvironmentVariable(
            name=option,
            default=default,
            help_text=documentation.help_text,
            group=documentation.group,
            auto_display_default=documentation.auto_display_default,
        )
        ENVVAR_REGISTRY[option] = variable

    if split:
        assert isinstance(default, Undefined | Sequence), (
            "You must provide a sequence default argument"
        )
        match default:
            case [t, *_]:
                return _config(
                    option,
                    cast=Csv(cast=cast if callable(cast) else type(t)),
                    default=_dumps(default),
                )
            case [] | "":
                return _config(
                    option,
                    cast=Csv(cast=cast if callable(cast) else lambda x: x),
                    default="",
                )
            case str(default):
                return _config(option, cast=Csv(), default=default)
            case _:
                if callable(cast):
                    return _config(option, cast=Csv(cast=cast))
                return _config(option, cast=Csv())

    # infer the ``cast`` from the default if not provided explicitly
    match (cast, default):
        #
        # cases without explicit cast
        #
        case Undefined(), Undefined():
            return _config(option)
        case Undefined(), None:
            # explicit `None` default values cannot be used as cast, ignore it.
            return _config(option, default=default)
        case Undefined(), _:
            return _config(option, default=default, cast=type(default))
        #
        # with explicit cast
        #
        case _, Undefined():
            return _config(option, cast=cast)
        case _, _:
            # the combination of a default + cast is odd and goes against the common
            # behaviour when it's derived from the default type - unfortunately we can't
            # simply take the ``str(default)``, as there's no guarantee that
            # ``default == cast(str(default))`` (e.g. ``cast=date.fromisoformat``
            # already falls apart)
            if not isinstance(default, str):
                raise TypeError(
                    "'default' must be a string when providing a cast callback"
                )
            return _config(option, default=default, cast=cast)
        case _:  # pragma: no cover
            assert_never((cast, default))


def _dumps(given_default: Sequence) -> str:
    # python-decouple Csv cast expects the default as a string -
    # serialize it again.
    fd = io.StringIO()
    csv.writer(fd, lineterminator="", quoting=csv.QUOTE_NONNUMERIC).writerow(
        given_default
    )
    fd.seek(0)
    default = fd.read()
    return default


ENVVAR_REQUIRED_GROUP = "Required"
ENVVAR_OPTIONAL_GROUP = "Optional"


@dataclass(slots=True)
class EnvironmentVariable:
    name: str
    default: object
    help_text: str
    group: str | None = None
    auto_display_default: bool = True

    def __post_init__(self):
        if not self.group:
            self.group = (
                ENVVAR_REQUIRED_GROUP
                if isinstance(self.default, Undefined)
                else ENVVAR_OPTIONAL_GROUP
            )


ENVVAR_REGISTRY: dict[str, EnvironmentVariable] = {}
