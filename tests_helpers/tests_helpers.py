from dataclasses import asdict, is_dataclass, dataclass
from typing import List, Type, TypeVar, Union

import pytest

from dataclass_factory_30.common import EllipsisType
from dataclass_factory_30.factory import OperatingFactory
from dataclass_factory_30.feature_requirement import (
    HAS_ANNOTATED,
    HAS_PARAM_SPEC,
    HAS_TYPE_ALIAS,
    PythonVersionRequirement,
)
from dataclass_factory_30.provider import Provider
from dataclass_factory_30.provider.model.basic_gen import CodeGenAccumulator
from dataclass_factory_30.struct_path import get_path

T = TypeVar("T")


class PytestVersionMarker:
    def __init__(self, requirement: PythonVersionRequirement):
        self.requirement = requirement

    def __call__(self, func):
        ver_str = '.'.join(map(str, self.requirement.min_version))

        return pytest.mark.skipif(
            not self.requirement,
            reason=f'Need Python >= {ver_str}'
        )(func)

    def __bool__(self):
        raise NotImplementedError


requires_annotated = PytestVersionMarker(HAS_ANNOTATED)
requires_type_alias = PytestVersionMarker(HAS_TYPE_ALIAS)
requires_param_spec = PytestVersionMarker(HAS_PARAM_SPEC)


class TestFactory(OperatingFactory):
    def __init__(self, recipe: List[Provider]):
        super().__init__(recipe)

    def _get_config_recipe(self) -> List[Provider]:
        return []

    provide = OperatingFactory._facade_provide


def raises_path(exc: Union[Type[Exception], Exception], func, *, path: Union[list, None, EllipsisType] = Ellipsis):
    exc_type = exc if isinstance(exc, type) else type(exc)

    with pytest.raises(exc_type) as exc_info:
        func()

    if not isinstance(exc, type):
        if is_dataclass(exc):
            assert asdict(exc_info.value) == asdict(exc)  # noqa
        else:
            raise TypeError("Can compare only dataclass instances")

    if not isinstance(path, EllipsisType):
        extracted_path = get_path(exc_info.value)
        if path is None:
            assert extracted_path is None
        else:
            assert extracted_path is not None
            assert list(extracted_path) == list(path)


def parametrize_bool(param: str, *params: str):
    full_params = [param, *params]

    def decorator(func):
        for p in full_params:
            func = pytest.mark.parametrize(
                p, [False, True],
                ids=[f'{p}=False', f'{p}=True']
            )(func)
        return func

    return decorator


@dataclass
class DebugCtx:
    accum: CodeGenAccumulator

    @property
    def source(self):
        return self.accum.list[-1][1].source

    @property
    def source_namespace(self):
        return self.accum.list[-1][1].namespace