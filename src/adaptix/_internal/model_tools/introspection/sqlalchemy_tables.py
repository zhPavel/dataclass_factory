from inspect import getfullargspec
from typing import Any, Optional

from sqlalchemy import inspect
from sqlalchemy.sql.schema import CallableColumnDefault, ScalarElementColumnDefault

from adaptix._internal.model_tools.definitions import (
    DefaultFactory,
    DefaultValue,
    FullShape,
    InputField,
    InputShape,
    NoDefault,
    OutputField,
    OutputShape,
    Param,
    ParamKind,
    Shape,
    create_attr_accessor,
)
from adaptix._internal.type_tools import get_all_type_hints


class ColumnPropertyWrapper:
    def __init__(self, column_property):
        self.column_property = column_property


def _is_context_sensitive(default):
    try:
        wrapped_callable = default.arg.__wrapped__
    except AttributeError:
        return True

    spec = getfullargspec(wrapped_callable)
    return len(spec.args) > 0


def _get_type_for_column(column, type_hints):
    try:
        return type_hints[column.name].__args__[0]
    except KeyError:
        if column.nullable:
            return Optional[column.type.python_type]
        return column.type.python_type


def _get_type_for_relationship(relationship, type_hints):
    try:
        return type_hints[str(relationship).split(".")[1]].__args__[0]
    except KeyError:
        return Any


def _get_default(column_default):
    if isinstance(column_default, CallableColumnDefault) and not _is_context_sensitive(column_default):
        return DefaultFactory(factory=column_default.arg.__wrapped__)
    if isinstance(column_default, ScalarElementColumnDefault):
        return DefaultValue(value=column_default.arg)
    return NoDefault()


def _get_input_required(column):
    return not (
        #  columns constrainted by FK are not required since they can be specified by instances
        column.default or column.nullable or column.server_default or column.foreign_keys
        or (column.primary_key and column.autoincrement and column.type.python_type is int)
    )


def _get_output_required(column):
    return not column.nullable


def _get_input_shape(tp, columns, relationships, type_hints) -> InputShape:
    fields = []
    params = []
    for column in columns:
        fields.append(
            InputField(
                id=column.name,
                type=_get_type_for_column(column, type_hints),
                default=_get_default(column.default),
                is_required=_get_input_required(column),
                metadata=column.info,
                original=ColumnPropertyWrapper(column_property=column)
            )
        )
        params.append(
            Param(
                field_id=column.name,
                name=column.name,
                kind=ParamKind.KW_ONLY
            )
        )

    for relationship in relationships:
        fields.append(
            InputField(
                id=relationship.key,
                type=_get_type_for_relationship(relationship, type_hints),
                default=NoDefault(),
                is_required=False,
                metadata={},
                original=relationship
            )
        )
        params.append(
            Param(
                field_id=relationship.key,
                name=relationship.key,
                kind=ParamKind.KW_ONLY
            )
        )

    return InputShape(
        constructor=tp,
        fields=tuple(fields),
        overriden_types=frozenset(),
        kwargs=None,
        params=tuple(params)
    )


def _get_output_shape(columns, relationships, type_hints) -> OutputShape:
    output_fields = [
        OutputField(
            id=column.name,
            type=_get_type_for_column(column, type_hints),
            default=_get_default(column.default),
            metadata=column.info,
            original=ColumnPropertyWrapper(column_property=column),
            accessor=create_attr_accessor(column.name, is_required=_get_output_required(column))
        )
        for column in columns
    ]

    for relationship in relationships:
        name = str(relationship).split(".")[1]
        output_fields.append(
            OutputField(
                id=name,
                type=_get_type_for_relationship(relationship, type_hints),
                default=NoDefault(),
                metadata={},
                original=relationship,
                accessor=create_attr_accessor(name, is_required=False)
            )
        )

    return OutputShape(
        fields=tuple(output_fields),
        overriden_types=frozenset()
    )


def get_sqlalchemy_shape(tp) -> FullShape:
    columns = inspect(tp).columns
    relationships = inspect(tp).relationships
    type_hints = get_all_type_hints(tp)
    return Shape(
        input=_get_input_shape(tp, columns, relationships, type_hints),
        output=_get_output_shape(columns, relationships, type_hints)
    )
