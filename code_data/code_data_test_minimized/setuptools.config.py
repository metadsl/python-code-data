import ast
import io
import os
import sys

import warnings
import functools
import importlib
from collections import defaultdict
from functools import partial
from functools import wraps
from glob import iglob
import contextlib

from distutils.errors import DistutilsOptionError, DistutilsFileError
from setuptools.extern.packaging.version import Version, InvalidVersion
from setuptools.extern.packaging.specifiers import SpecifierSet


class StaticModule:
    """
    Attempt to load the module by the name
    """

    def __init__(self, name):
        spec = importlib.util.find_spec(name)
        with open(spec.origin) as strm:
            src = strm.read()
        module = ast.parse(src)
        vars(self).update(locals())
        del self.self

    def __getattr__(self, attr):
        try:
            return next(
                ast.literal_eval(statement.value)
                for statement in self.module.body
                if isinstance(statement, ast.Assign)
                for target in statement.targets
                if isinstance(target, ast.Name) and target.id == attr
            )
        except Exception as e:
            raise AttributeError(
                "{self.name} has no attribute {attr}".format(**locals())
            ) from e


@contextlib.contextmanager
def patch_path(path):
    """
    Add path to front of sys.path for the duration of the context.
    """
    try:
        sys.path.insert(0, path)
        yield
    finally:
        sys.path.remove(path)


def read_configuration(filepath, find_others=False, ignore_option_errors=False):
    """Read given configuration file and returns options from it as a dict.

    :param str|unicode filepath: Path to configuration file
        to get options from.

    :param bool find_others: Whether to search for other configuration files
        which could be on in various places.

    :param bool ignore_option_errors: Whether to silently ignore
        options, values of which could not be resolved (e.g. due to exceptions
        in directives such as file:, attr:, etc.).
        If False exceptions are propagated as expected.

    :rtype: dict
    """
    from setuptools.dist import Distribution, _Distribution

    filepath = os.path.abspath(filepath)

    if not os.path.isfile(filepath):
        raise DistutilsFileError('Configuration file %s does not exist.' % filepath)

    current_directory = os.getcwd()
    os.chdir(os.path.dirname(filepath))

    try:
        dist = Distribution()

        filenames = dist.find_config_files() if find_others else []
        if filepath not in filenames:
            filenames.append(filepath)

        _Distribution.parse_config_files(dist, filenames=filenames)

        handlers = parse_configuration(
            dist, dist.command_options, ignore_option_errors=ignore_option_errors
        )

    finally:
        os.chdir(current_directory)

    return configuration_to_dict(handlers)


def _get_option(target_obj, key):
    """
    Given a target object and option key, get that option from
    the target object, either through a get_{key} method or
    from an attribute directly.
    """
    getter_name = 'get_{key}'.format(**locals())
    by_attribute = functools.partial(getattr, target_obj, key)
    getter = getattr(target_obj, getter_name, by_attribute)
    return getter()


def configuration_to_dict(handlers):
    """Returns configuration data gathered by given handlers as a dict.

    :param list[ConfigHandler] handlers: Handlers list,
        usually from parse_configuration()

    :rtype: dict
    """
    config_dict = defaultdict(dict)

    for handler in handlers:
        for option in handler.set_options:
            value = _get_option(handler.target_obj, option)
            config_dict[handler.section_prefix][option] = value

    return config_dict


def parse_configuration(distribution, command_options, ignore_option_errors=False):
    """Performs additional parsing of configuration options
    for a distribution.

    Returns a list of used option handlers.

    :param Distribution distribution:
    :param dict command_options:
    :param bool ignore_option_errors: Whether to silently ignore
        options, values of which could not be resolved (e.g. due to exceptions
        in directives such as file:, attr:, etc.).
        If False exceptions are propagated as expected.
    :rtype: list
    """
    options = ConfigOptionsHandler(distribution, command_options, ignore_option_errors)
    options.parse()

    meta = ConfigMetadataHandler(
        distribution.metadata,
        command_options,
        ignore_option_errors,
        distribution.package_dir,
    )
    meta.parse()

    return meta, options


class ConfigHandler:
    """Handles metadata supplied in configuration files."""

    section_prefix = None
    """Prefix for config sections handled by this handler.
    Must be provided by class heirs.

    """

    aliases = {}
    """Options aliases.
    For compatibility with various packages. E.g.: d2to1 and pbr.
    Note: `-` in keys is replaced with `_` by config parser.

    """

    def __init__(self, target_obj, options, ignore_option_errors=False):
        sections = {}

        section_prefix = self.section_prefix
        for section_name, section_options in options.items():
            if not section_name.startswith(section_prefix):
                continue

            section_name = section_name.replace(section_prefix, '').strip('.')
            sections[section_name] = section_options

        self.ignore_option_errors = ignore_option_errors
        self.target_obj = target_obj
        self.sections = sections
        self.set_options = []

    @property
    def parsers(self):
        """Metadata item name to parser function mapping."""
        raise NotImplementedError(
            '%s must provide .parsers property' % self.__class__.__name__
        )

    def __setitem__(self, option_name, value):
        unknown = tuple()
        target_obj = self.target_obj

        # Translate alias into real name.
        option_name = self.aliases.get(option_name, option_name)

        current_value = getattr(target_obj, option_name, unknown)

        if current_value is unknown:
            raise KeyError(option_name)

        if current_value:
            # Already inhabited. Skipping.
            return

        skip_option = False
        parser = self.parsers.get(option_name)
        if parser:
            try:
                value = parser(value)

            except Exception:
                skip_option = True
                if not self.ignore_option_errors:
                    raise

        if skip_option:
            return

        setter = getattr(target_obj, 'set_%s' % option_name, None)
        if setter is None:
            setattr(target_obj, option_name, value)
        else:
            setter(value)

        self.set_options.append(option_name)

    @classmethod
    def _parse_list(cls, value, separator=','):
        """Represents value as a list.

        Value is split either by separator (defaults to comma) or by lines.

        :param value:
        :param separator: List items separator character.
        :rtype: list
        """
        if isinstance(value, list):  # _get_parser_compound case
            return value

        if '\n' in value:
            value = value.splitlines()
        else:
            value = value.split(separator)

        return [chunk.strip() for chunk in value if chunk.strip()]

    @classmethod
    def _parse_list_glob(cls, value, separator=','):
        """Equivalent to _parse_list() but expands any glob patterns using glob().

        However, unlike with glob() calls, the results remain relative paths.

        :param value:
        :param separator: List items separator character.
        :rtype: list
        """
        glob_characters = ('*', '?', '[', ']', '{', '}')
        values = cls._parse_list(value, separator=separator)
        expanded_values = []
        for value in values:

            # Has globby characters?
            if any(char in value for char in glob_characters):
                # then expand the glob pattern while keeping paths *relative*:
                expanded_values.extend(sorted(
                    os.path.relpath(path, os.getcwd())
                    for path in iglob(os.path.abspath(value))))

            else:
                # take the value as-is:
                expanded_values.append(value)

        return expanded_values

    @classmethod
    def _parse_dict(cls, value):
        """Represents value as a dict.

        :param value:
        :rtype: dict
        """
        separator = '='
        result = {}
        for line in cls._parse_list(value):
            key, sep, val = line.partition(separator)
            if sep != separator:
                raise DistutilsOptionError(
                    'Unable to parse option value to dict: %s' % value
                )
            result[key.strip()] = val.strip()

        return result

    @classmethod
    def _parse_bool(cls, value):
        """Represents value as boolean.

        :param value:
        :rtype: bool
        """
        value = value.lower()
        return value in ('1', 'true', 'yes')

    @classmethod
    def _exclude_files_parser(cls, key):
        """Returns a parser function to make sure field inputs
        are not files.

        Parses a value after getting the key so error messages are
        more informative.

        :param key:
        :rtype: callable
        """

        def parser(value):
            exclude_directive = 'file:'
            if value.startswith(exclude_directive):
                raise ValueError(
                    'Only strings are accepted for the {0} field, '
                    'files are not accepted'.format(key)
                )
            return value

        return parser

    @classmethod
    def _parse_file(cls, value):
        """Represents value as a string, allowing including text
        from nearest files using `file:` directive.

        Directive is sandboxed and won't reach anything outside
        directory with setup.py.

        Examples:
            file: README.rst, CHANGELOG.md, src/file.txt

        :param str value:
        :rtype: str
        """
        include_directive = 'file:'

        if not isinstance(value, str):
            return value

        if not value.startswith(include_directive):
            return value

        spec = value[len(include_directive) :]
        filepaths = (os.path.abspath(path.strip()) for path in spec.split(','))
        return '\n'.join(
            cls._read_file(path)
            for path in filepaths
            if (cls._assert_local(path) or True) and os.path.isfile(path)
        )