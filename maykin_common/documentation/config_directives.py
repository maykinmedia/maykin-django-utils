import warnings
from collections import defaultdict
from collections.abc import Callable, Collection
from typing import ClassVar

from decouple import Undefined, undefined
from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.parsers.rst.states import RSTState
from docutils.statemachine import ViewList

from maykin_common.config import (
    ENVVAR_OPTIONAL_GROUP,
    ENVVAR_REGISTRY,
    ENVVAR_REQUIRED_GROUP,
    EnvironmentVariable,
)

type OptionSpec = dict[str, Callable[[str], object]] | None


def get_envvar(param_name: str) -> EnvironmentVariable:
    """
    Get an environment variable and its metadata from the registry by name

    :arg param_name: name of the environment variable
    :returns: the environment variable with metadata for documentation
    """
    var = ENVVAR_REGISTRY.get(param_name)
    if not var:
        raise ValueError(f"Envvar with name {param_name} not found in registry")
    return var


def get_envvar_group(
    group_name: str,
    members: Collection[str] | None = None,
    exclude: Collection[str] | None = None,
) -> list[EnvironmentVariable]:
    """
    Get a list of environment variables and their metadata from
    the registry by group name

    :arg group_name: name of the environment variable group
    :arg members: name(s) of the environment variable to include from the group
    :arg exclude: name(s) of the environment variable to exclude from the group
    :returns: the list of environment variables with metadata for documentation
    """
    variables = (v for v in ENVVAR_REGISTRY.values() if v.group == group_name)
    if members:
        variables = (v for v in variables if v.name in members)
    if exclude:
        variables = (v for v in variables if v.name not in exclude)
    return list(variables)


def document_param(
    var: EnvironmentVariable,
    state: RSTState,
    default: str | None | Undefined = undefined,
) -> nodes.Node:
    """
    Create an rST node to document an environment variable

    :arg var: the environment variable metadata
    :arg state: the reStructuredText state machine state
    :arg default: an optional override for the default of the environment variable
    :returns: the node with a list item to document the environment variable
    """
    para = nodes.paragraph()

    result = f"``{var.name}``: "

    if var.help_text:
        result += var.help_text
        if not var.help_text.endswith("."):
            result += "."
    else:
        warnings.warn(f"missing help_text for environment variable {var}", stacklevel=2)

    if var.auto_display_default:
        # Use explicitly provided default to override the default defined in code
        default_value = default if default is not undefined else var.default
        match default_value:
            case Undefined():
                pass
            case "" | []:
                result += " Defaults to: ``(empty string)``."
            case str(text):
                result += f" Defaults to: ``{text}``."
            case [*values]:
                result += f" Defaults to: ``{','.join(map(str, values))}``."
            case other:
                result += f" Defaults to: ``{other}``."

    # Make sure the line is rendered as rST
    vl = ViewList()
    vl.append(var.help_text, "<param_help>")
    text, _ = state.inline_text(result, 0)
    para += text

    # TODO cleaner way to do this?
    para += nodes.raw("", "<br>", format="html")

    item = nodes.list_item()
    item += para
    return item


def document_group(
    group: Collection[EnvironmentVariable], state: RSTState
) -> nodes.Node:
    """
    Create an rST node to document a group of environment variables

    :arg group: the list of environment variables with metadata
    :arg state: the reStructuredText state machine state
    :returns: the node with list items to document the environment variables
    """
    bullet_list = nodes.bullet_list()
    for var in group:
        bullet_list += document_param(var, state)
    return bullet_list


class ConfigParamDirective(Directive):
    """
    Directive to generate documentation for a specific parameter (environment variable)

    :arg default: override the default of the environment variable
    :returns: the node with a list item to document the environment variable
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True

    option_spec: ClassVar[OptionSpec] = {
        "default": directives.unchanged,
    }

    def run(self):
        param_name = self.arguments[0]
        default = self.options.get("default", undefined)

        var = get_envvar(param_name)
        para = document_param(var, self.state, default=default)

        return [para]


class ConfigGroupDirective(Directive):
    """
    Directive to generate documentation for a specific parameter group

    :arg members: the names of the environment variables from the group that should be
        displayed
    :arg exclude: the names of the environment variables from the group that should not
        be displayed
    :returns: the node with list items to document the environment variables
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True

    option_spec: ClassVar[OptionSpec] = {
        "members": directives.unchanged,
        "exclude": directives.unchanged,
    }

    def run(self):
        group_name = self.arguments[0]

        # Get members and split by comma, stripping extra whitespace
        members_str = self.options.get("members", "")
        members = [m.strip() for m in members_str.split(",") if m.strip()]

        # Same for exclude
        exclude_str = self.options.get("exclude", "")
        exclude = [e.strip() for e in exclude_str.split(",") if e.strip()]

        if members and exclude:
            raise ValueError("cannot use both `members` and `exclude` options")

        group = get_envvar_group(group_name, members=members, exclude=exclude)

        return [document_group(group, self.state)]


class ConfigAllParamsDirective(Directive):
    """
    Directive to generate documentation for all parameter groups

    :arg members-groups: the names of the environment variable groups that should be
        displayed
    :arg exclude-groups: the names of the environment variable groups that should not be
        displayed
    :arg exclude-groups: the names of the environment variables that should not be
        displayed
    :returns: the node with sections to document the environment variables per group
    """

    has_content = False
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = True

    option_spec: ClassVar[OptionSpec] = {
        "members-groups": directives.unchanged,
        "exclude-groups": directives.unchanged,
        "exclude-params": directives.unchanged,
    }

    def run(self):
        members_groups = self.options.get("members-groups", "")
        exclude_groups = self.options.get("exclude-groups", "")
        exclude_params = self.options.get("exclude-params", "")

        if members_groups and exclude_groups:
            raise ValueError(
                "cannot use both `members-groups` and `exclude-groups` options"
            )

        grouped_vars = defaultdict(list)
        for var in ENVVAR_REGISTRY.values():
            # Check if the group should be included
            if (
                members_groups
                and var.group not in members_groups
                or exclude_groups
                and var.group in exclude_groups
            ):
                continue

            # Check if the param should be included
            if var.name in exclude_params:
                continue

            grouped_vars[var.group].append(var)

        root = nodes.container()

        def handle_group(group_name, variables, root):
            group = nodes.section()
            group["ids"].append(group_name)

            group += nodes.title(text=group_name)
            group += document_group(variables, self.state)
            root += group

        # Make sure the required vars are listed first
        if required_vars := grouped_vars.pop(ENVVAR_REQUIRED_GROUP, None):
            handle_group(ENVVAR_REQUIRED_GROUP, required_vars, root)

        optional_vars = grouped_vars.pop(ENVVAR_OPTIONAL_GROUP, None)
        for group_name, variables in grouped_vars.items():
            handle_group(group_name, variables, root)

        # Make sure the optional vars are listed first
        if optional_vars:
            handle_group(ENVVAR_OPTIONAL_GROUP, optional_vars, root)

        return [root]


def setup(app):  # pragma: no cover
    app.add_directive("config-param", ConfigParamDirective)
    app.add_directive("config-group", ConfigGroupDirective)
    app.add_directive("config-all-params", ConfigAllParamsDirective)
