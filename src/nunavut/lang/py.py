#
# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Copyright (C) 2018-2019  UAVCAN Development Team  <uavcan.org>
# This software is distributed under the terms of the MIT License.
#
"""
    Filters for generating python. All filters in this
    module will be available in the template's global namespace as ``py``.
"""
import builtins
import functools
import keyword
import typing

import pydsdl

from ..templates import (SupportsTemplateContext, template_context_filter,
                         template_language_filter, template_language_int_filter,
                         template_language_list_filter)
from . import Language, _UniqueNameGenerator
from .c import VariableNameEncoder


@template_context_filter
def filter_to_template_unique_name(context: SupportsTemplateContext, base_token: str) -> str:
    """
    Filter that takes a base token and forms a name that is very
    likely to be unique within the template the filter is invoked. This
    name is also very likely to be a valid Python identifier.

    .. IMPORTANT::

        The exact tokens generated may change between major or minor versions
        of this library. The only guarantee provided is that the tokens
        will be stable for the same version of this library given the same
        input.

        Also note that name uniqueness is only likely within a given template.
        Between templates there is no guarantee of uniqueness and,
        since this library does not lex generated source, there is no guarantee
        that the generated name does not conflict with a name generated by
        another means.

    .. invisible-code-block: python

        from nunavut.lang.py import filter_to_template_unique_name

    .. code-block:: python

        # Given
        template  = '{{ "f" | to_template_unique_name }},{{ "f" | to_template_unique_name }},'
        template += '{{ "f" | to_template_unique_name }},{{ "bar" | to_template_unique_name }}'

        # then
        rendered = '_f0_,_f1_,_f2_,_bar0_'

    .. invisible-code-block: python

        jinja_filter_tester(filter_to_template_unique_name, template, rendered, 'py')

    .. code-block:: python

        # Given
        template = '{{ "i like coffee" | to_template_unique_name }}'

        # then
        rendered = '_i like coffee0_'

    .. invisible-code-block: python

        jinja_filter_tester(filter_to_template_unique_name, template, rendered, 'py')

    :param str base_token: A token to include in the base name.
    :returns: A name that is likely to be valid python identifier and is likely to
        be unique within the file generated by the current template.
    """
    return _UniqueNameGenerator.get_instance()('py', base_token, '_', '_')


PYTHON_RESERVED_IDENTIFIERS = frozenset(map(str, list(keyword.kwlist) + dir(builtins)))  # type: typing.FrozenSet[str]


@template_language_filter(__name__)
def filter_id(language: Language,
              instance: typing.Any) -> str:
    """
    Filter that produces a valid Python identifier for a given object. The encoding may not
    be reversable.

    .. invisible-code-block: python

        from nunavut.lang.py import filter_id

    .. code-block:: python

        # Given
        I = 'I like python'

        # and
        template = '{{ I | id }}'

        # then
        rendered = 'I_like_python'


    .. invisible-code-block: python

        jinja_filter_tester(filter_id, template, rendered, 'py', I=I)

    .. code-block:: python

        # Given
        I = '&because'

        # and
        template = '{{ I | id }}'

        # then
        rendered = 'ZX0026because'


    .. invisible-code-block: python

        jinja_filter_tester(filter_id, template, rendered, 'py', I=I)


    .. code-block:: python

        # Given
        I = 'if'

        # and
        template = '{{ I | id }}'

        # then
        rendered = 'if_'


    .. invisible-code-block: python

        jinja_filter_tester(filter_id, template, rendered, 'py', I=I)


    :param any instance:        Any object or data that either has a name property or can be converted
                                to a string.
    :returns: A token that is a valid Python identifier, is not a reserved keyword, and is transformed
              in a deterministic manner based on the provided instance.
    """
    if hasattr(instance, 'name'):
        raw_name = str(instance.name)  # type: str
    else:
        raw_name = str(instance)

    # We use the C variable name encoder since the variable token rules are
    # compatible.
    reserved = set(language.get_reserved_identifiers())
    reserved.update(PYTHON_RESERVED_IDENTIFIERS)
    vne = VariableNameEncoder(language.stropping_prefix,
                              language.stropping_suffix,
                              language.encoding_prefix,
                              False)
    return vne.strop(raw_name, frozenset(reserved))


@template_language_filter(__name__)
def filter_full_reference_name(language: Language, t: pydsdl.CompositeType) -> str:
    """
    Provides a string that is the full namespace, typename, major, and minor version for a given composite type.

    .. invisible-code-block: python

        from nunavut.lang.py import filter_full_reference_name

        dummy = lambda: None
        dummy_version = lambda: None
        setattr(dummy, 'version', dummy_version)

    .. code-block:: python

        # Given
        full_name = 'any.str.2Foo'
        major = 1
        minor = 2

        # and
        template = '{{ my_obj | full_reference_name }}'

        # then
        rendered = 'any_.str_._2Foo_1_2'

    .. invisible-code-block: python


        setattr(dummy_version, 'major', major)
        setattr(dummy_version, 'minor', minor)
        setattr(dummy, 'full_name', full_name)
        setattr(dummy, 'short_name', full_name.split('.')[-1])
        jinja_filter_tester(filter_full_reference_name, template, rendered, 'py', my_obj=dummy)


    :param pydsdl.CompositeType t: The DSDL type to get the fully-resolved reference name for.
    """
    ns_parts = t.full_name.split('.')
    if len(ns_parts) > 1:
        if language.enable_stropping:
            ns = list(map(functools.partial(filter_id, language), ns_parts[:-1]))
        else:
            ns = ns_parts[:-1]

    return '.'.join(ns + [filter_short_reference_name(language, t)])


@template_language_filter(__name__)
def filter_short_reference_name(language: Language, t: pydsdl.CompositeType) -> str:
    """
    Provides a string that is a shorted version of the full reference name. This type is unique only within its
    namespace.

     .. invisible-code-block: python

        from nunavut.lang.py import filter_short_reference_name

        dummy = lambda: None
        dummy_version = lambda: None
        setattr(dummy, 'version', dummy_version)

    .. code-block:: python

        # Given
        short_name = '2Foo'
        major = 1
        minor = 2

        # and
        template = '{{ my_obj | short_reference_name }}'

        # then
        rendered = '_2Foo_1_2'

    .. invisible-code-block: python

        setattr(dummy_version, 'major', major)
        setattr(dummy_version, 'minor', minor)
        setattr(dummy, 'short_name', short_name)
        jinja_filter_tester(filter_short_reference_name, template, rendered, 'py', my_obj=dummy)


    :param pydsdl.CompositeType t: The DSDL type to get the reference name for.
    """
    short_name = '{short}_{major}_{minor}'.format(short=t.short_name, major=t.version.major, minor=t.version.minor)
    if language.enable_stropping:
        return filter_id(language, short_name)
    else:
        return short_name


def filter_alignment_prefix(offset: pydsdl.BitLengthSet) -> str:
    """
    Provides a string prefix based on a given :class:`pydsdl.BitLengthSet`.

    .. invisible-code-block: python

        from nunavut.lang.py import filter_alignment_prefix
        import pydsdl

    .. code-block:: python

        # Given
        B = pydsdl.BitLengthSet(32)

        # and
        template = '{{ B | alignment_prefix }}'

        # then ('str' is stropped to 'str_' before the version is suffixed)
        rendered = 'aligned'

    .. invisible-code-block: python

        jinja_filter_tester(filter_alignment_prefix, template, rendered, 'py', B=B)


    .. code-block:: python

        # Given
        B = pydsdl.BitLengthSet(32)
        B.increment(1)

        # and
        template = '{{ B | alignment_prefix }}'

        # then ('str' is stropped to 'str_' before the version is suffixed)
        rendered = 'unaligned'

    .. invisible-code-block: python

        jinja_filter_tester(filter_alignment_prefix, template, rendered, 'py', B=B)


    :param pydsdl.BitLengthSet offset: A bit length set to test for alignment.
    :return: 'aligned' or 'unaligned' based on the state of the ``offset`` argument.
    """
    if isinstance(offset, pydsdl.BitLengthSet):
        return 'aligned' if offset.is_aligned_at_byte() else 'unaligned'
    else:  # pragma: no cover
        raise TypeError('Expected BitLengthSet, got {}'.format(type(offset).__name__))


@template_language_list_filter(__name__)
def filter_imports(language: Language,
                   t: pydsdl.CompositeType,
                   sort: bool = True) -> typing.List[str]:
    """
    Returns a list of all modules that must be imported to use a given type.

    :param pydsdl.CompositeType t: The type to scan for dependencies.
    :param bool sort: If true the returned list will be sorted.
    :return: a list of python module names the provided type depends on.
    """
    # Make a list of all attributes defined by this type
    if isinstance(t, pydsdl.ServiceType):
        atr = t.request_type.attributes + t.response_type.attributes
    else:
        atr = t.attributes

    def array_w_composite_type(data_type: pydsdl.Any) -> bool:
        return isinstance(data_type, pydsdl.ArrayType) and isinstance(data_type.element_type, pydsdl.CompositeType)

    # Extract data types of said attributes; for type constructors such as arrays extract the element type
    dep_types = [x.data_type for x in atr if isinstance(x.data_type, pydsdl.CompositeType)]
    dep_types += [x.data_type.element_type for x in atr if array_w_composite_type(x.data_type)]

    # Make a list of unique full namespaces of referenced composites
    namespace_list = [x.full_namespace for x in dep_types]

    if language.enable_stropping:
        namespace_list = ['.'.join([filter_id(language, y) for y in x.split('.')]) for x in namespace_list]

    if sort:
        return list(sorted(namespace_list))
    else:
        return namespace_list


@template_language_int_filter(__name__)
def filter_longest_id_length(language: Language,
                             attributes: typing.List[pydsdl.Attribute]) -> int:
    """
    Return the length of the longest identifier in a list of :class:`pydsdl.Attribute` objects.

    .. invisible-code-block: python

        from nunavut.lang.py import filter_longest_id_length


    .. code-block:: python

        # Given
        I = ['one.str.int.any', 'three.str.int.any']

        # and
        template = '{{ I | longest_id_length }}'

        # then
        rendered = '32'

    .. invisible-code-block: python

        jinja_filter_tester(filter_longest_id_length, template, rendered, 'py', I=I)


    """
    if language.enable_stropping:
        return max(map(len, map(functools.partial(filter_id, language), attributes)))
    else:
        return max(map(len, attributes))


def filter_bit_length_set(values: typing.Optional[typing.Union[typing.Iterable[int], int]]) -> pydsdl.BitLengthSet:
    """
    Convert an integer or a list of integers into a :class:`pydsdl.BitLengthSet`.

    .. invisible-code-block: python

        from nunavut.lang.py import filter_bit_length_set
        import pydsdl

        assert type(filter_bit_length_set(23)) == pydsdl.BitLengthSet

    """
    return pydsdl.BitLengthSet(values)
