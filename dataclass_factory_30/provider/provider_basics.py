import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from inspect import isabstract
from typing import Any, Callable, ClassVar, Generic, Iterable, Pattern, Sequence, Type, TypeVar, Union

from ..common import TypeHint
from ..type_tools import is_parametrized, is_protocol, is_subclass_soft, normalize_type
from ..type_tools.normalize_type import BaseNormType, NormTV, NotSubscribedError
from .essential import CannotProvide, Mediator, Provider, Request
from .request_cls import FieldRM, TypeHintRM

T = TypeVar('T')


class RequestChecker(ABC):
    @abstractmethod
    def check_request(self, mediator: Mediator[T], request: Request[T]) -> None:
        """Raise CannotProvide if the request does not meet the conditions"""

    def __or__(self, other: 'RequestChecker') -> 'RequestChecker':
        return OrRequestChecker([self, other])

    def __and__(self, other: 'RequestChecker') -> 'RequestChecker':
        return AndRequestChecker([self, other])

    def __xor__(self, other: 'RequestChecker') -> 'RequestChecker':
        return XorRequestChecker(self, other)

    def __neg__(self) -> 'RequestChecker':
        return NegRequestChecker(self)


class OrRequestChecker(RequestChecker):
    def __init__(self, request_checkers: Iterable[RequestChecker]):
        self._request_checkers = request_checkers

    def check_request(self, mediator: Mediator[T], request: Request[T]) -> None:
        sub_errors = []

        for checker in self._request_checkers:
            try:
                checker.check_request(mediator, request)
            except CannotProvide as e:
                sub_errors.append(e)
            else:
                return

        raise CannotProvide(sub_errors=sub_errors)


class AndRequestChecker(RequestChecker):
    def __init__(self, request_checkers: Iterable[RequestChecker]):
        self._request_checkers = request_checkers

    def check_request(self, mediator: Mediator[T], request: Request[T]) -> None:
        for checker in self._request_checkers:
            checker.check_request(mediator, request)


class NegRequestChecker(RequestChecker):
    def __init__(self, rc: RequestChecker):
        self._rc = rc

    def check_request(self, mediator: Mediator[T], request: Request[T]) -> None:
        try:
            self._rc.check_request(mediator, request)
        except CannotProvide:
            return
        else:
            raise CannotProvide


class XorRequestChecker(RequestChecker):
    def __init__(self, left: RequestChecker, right: RequestChecker):
        self._left = left
        self._right = right

    def check_request(self, mediator: Mediator[T], request: Request[T]) -> None:
        exceptions = []

        try:
            self._left.check_request(mediator, request)
        except CannotProvide as exc:
            exceptions.append(exc)

        try:
            self._right.check_request(mediator, request)
        except CannotProvide as exc:
            exceptions.append(exc)

        if len(exceptions) == 0:
            raise CannotProvide

        if len(exceptions) == 2:
            raise CannotProvide(sub_errors=exceptions)


class BoundedRequestChecker(RequestChecker, ABC):
    BOUND: ClassVar[Type[Request]]

    def check_request(self, mediator: Mediator[T], request: Request[T]) -> None:
        if isinstance(request, self.BOUND):
            self._check_bounded_request(mediator, request)
        else:
            raise CannotProvide(f'Only instances of {self.BOUND} is allowed')

    @abstractmethod
    def _check_bounded_request(self, mediator: Mediator, request: Any) -> None:
        pass


@dataclass
class ExactFieldNameRC(BoundedRequestChecker):
    BOUND = FieldRM
    field_name: str

    def _check_bounded_request(self, mediator: Mediator, request: FieldRM) -> None:
        if self.field_name == request.field.name:
            return
        raise CannotProvide(f'field_name must be a {self.field_name!r}')


@dataclass
class ReFieldNameRC(BoundedRequestChecker):
    BOUND = FieldRM
    pattern: Pattern[str]

    def _check_bounded_request(self, mediator: Mediator, request: FieldRM) -> None:
        if self.pattern.fullmatch(request.field.name):
            return

        raise CannotProvide(f'field_name must be matched by {self.pattern!r}')


@dataclass
class ExactTypeRC(BoundedRequestChecker):
    BOUND = TypeHintRM
    norm: BaseNormType

    def _check_bounded_request(self, mediator: Mediator, request: TypeHintRM) -> None:
        if normalize_type(request.type) == self.norm:
            return
        raise CannotProvide(f'{request.type} must be a equal to {self.norm.source}')


@dataclass
class SubclassRC(BoundedRequestChecker):
    BOUND = TypeHintRM
    type_: type

    def _check_bounded_request(self, mediator: Mediator, request: TypeHintRM) -> None:
        norm = normalize_type(request.type)
        if is_subclass_soft(norm.origin, self.type_):
            return
        raise CannotProvide(f'{request.type} must be a subclass of {self.type_}')


@dataclass
class ExactOriginRC(BoundedRequestChecker):
    BOUND = TypeHintRM
    origin: Any

    def _check_bounded_request(self, mediator: Mediator, request: TypeHintRM) -> None:
        if normalize_type(request.type).origin == self.origin:
            return
        raise CannotProvide(f'{request.type} must have origin {self.origin}')


@dataclass
class StackEndRC(RequestChecker):
    request_checkers: Sequence[RequestChecker]

    def check_request(self, mediator: Mediator[T], request: Request[T]) -> None:
        stack = mediator.request_stack
        offset = len(stack) - len(self.request_checkers)

        if offset < 0:
            raise CannotProvide("Request stack is too small")

        for checker, stack_request in zip(self.request_checkers, stack[offset:]):
            checker.check_request(mediator, stack_request)


class AnyRequestChecker(RequestChecker):
    def check_request(self, mediator: Mediator[T], request: Request[T]) -> None:
        return


def match_origin(tp: TypeHint) -> RequestChecker:
    if is_parametrized(tp):
        raise ValueError("Origin must be not parametrized")

    try:
        origin = normalize_type(tp).origin
    except NotSubscribedError:
        origin = tp

    if is_protocol(origin) or isabstract(origin):
        return SubclassRC(origin)

    return ExactOriginRC(origin)


def create_type_hint_req_checker(tp: TypeHint) -> RequestChecker:
    try:
        norm = normalize_type(tp)
    except NotSubscribedError:
        return ExactOriginRC(tp)
    except ValueError:
        raise ValueError(f'Can not create RequestChecker from {tp}')

    if isinstance(norm, NormTV):
        raise ValueError(f'Can not create RequestChecker from {tp}')

    return ExactTypeRC(norm)


def create_req_checker(pred: Union[TypeHint, str, RequestChecker]) -> RequestChecker:
    if isinstance(pred, str):
        if pred.isidentifier():
            return ExactFieldNameRC(pred)  # this is only an optimization
        return ReFieldNameRC(re.compile(pred))

    if isinstance(pred, re.Pattern):
        return ReFieldNameRC(pred)

    if isinstance(pred, RequestChecker):
        return pred

    return create_type_hint_req_checker(pred)


class BoundingProvider(Provider):
    def __init__(self, request_checker: RequestChecker, provider: Provider):
        self._request_checker = request_checker
        self._provider = provider

    def apply_provider(self, mediator: Mediator, request: Request[T]) -> T:
        self._request_checker.check_request(mediator, request)
        return self._provider.apply_provider(mediator, request)

    def __repr__(self):
        return f"{type(self).__name__}({self._request_checker}, {self._provider})"


class ValueProvider(Provider, Generic[T]):
    def __init__(self, req_cls: Type[Request[T]], value: T):
        self._req_cls = req_cls
        self._value = value

    def apply_provider(self, mediator: Mediator, request: Request):
        if not isinstance(request, self._req_cls):
            raise CannotProvide

        return self._value

    def __repr__(self):
        return f"{type(self).__name__}({self._req_cls}, {self._value})"


class FactoryProvider(Provider, Generic[T]):
    def __init__(self, req_cls: Type[Request[T]], factory: Callable[[], T]):
        self._req_cls = req_cls
        self._factory = factory

    def apply_provider(self, mediator: Mediator, request: Request):
        if not isinstance(request, self._req_cls):
            raise CannotProvide

        return self._factory()

    def __repr__(self):
        return f"{type(self).__name__}({self._req_cls}, {self._factory})"


class MergingProvider(Provider):
    def __init__(self, *providers: Provider):
        self._providers = providers

    def apply_provider(self, mediator: Mediator[T], request: Request[T]) -> T:
        errors = []

        for provider in self._providers:
            try:
                return provider.apply_provider(mediator, request)
            except CannotProvide as e:
                errors.append(e)

        raise CannotProvide(sub_errors=errors)

    def __repr__(self):
        return f"{type(self).__name__}({self._providers})"


class Chain(Enum):
    FIRST = 'FIRST'
    LAST = 'LAST'


class ChainingProvider(Provider):
    def __init__(self, chain: Chain, provider: Provider):
        self._chain = chain
        self._provider = provider

    def apply_provider(self, mediator: Mediator[T], request: Request[T]) -> T:
        current_processor = self._provider.apply_provider(mediator, request)
        next_processor = mediator.provide_from_next()

        if self._chain == Chain.FIRST:
            return self._make_chain(current_processor, next_processor)
        if self._chain == Chain.LAST:
            return self._make_chain(next_processor, current_processor)
        raise ValueError

    def _make_chain(self, first, second):
        def chain_processor(data):
            return second(first(data))

        return chain_processor
