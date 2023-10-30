# pylint: disable=import-outside-toplevel
import typing
from dataclasses import InitVar
from typing import ClassVar, Final

from ..feature_requirement import HAS_ANNOTATED, HAS_TYPED_DICT_REQUIRED
from .normalize_type import BaseNormType

_TYPE_TAGS = [Final, ClassVar, InitVar]

if HAS_ANNOTATED:
    _TYPE_TAGS.append(typing.Annotated)

if HAS_TYPED_DICT_REQUIRED:
    _TYPE_TAGS.extend([typing.Required, typing.NotRequired])


def strip_tags(norm: BaseNormType) -> BaseNormType:
    """Removes type hints that do not represent a type
    and that only indicates metadata
    """
    if norm.origin in _TYPE_TAGS:
        return strip_tags(norm.args[0])
    return norm


def is_class_var(norm: BaseNormType) -> bool:
    if norm.origin == ClassVar:
        return True
    if norm.origin in _TYPE_TAGS:
        return is_class_var(norm.args[0])
    return False
