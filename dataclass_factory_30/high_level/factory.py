from typing import Type, TypeVar, Any, Optional, List, Dict

from ..common import Parser, Serializer
from ..core import Request, Mediator, CannotProvide, Provider
from ..low_level import ExtraVariant
from ..low_level.builtin_factory import BuiltinFactory, ProvidingFromRecipe
from ..low_level.fields import DefaultExtra, CfgDefaultExtra
from ..low_level.incremental_factory import NoSuitableProvider, ConfigProvider
from ..low_level.mediator import RecursionResolving, StubsRecursionResolver
from ..low_level.request_cls import ParserRequest, SerializerRequest, CfgOmitDefault
from ..low_level.static_provider import static_provision_action

T = TypeVar('T')

RequestTV = TypeVar('RequestTV', bound=Request)


def create_factory_provision_action(request_cls: Type[RequestTV]):
    # noinspection PyUnusedLocal
    @static_provision_action(request_cls)
    def _provide_factory_proxy(
        self: ProvidingFromRecipe,
        mediator: Mediator,
        request: ParserRequest
    ):
        try:
            return self._provide_from_recipe(request)
        except NoSuitableProvider:
            raise CannotProvide

    return _provide_factory_proxy


class FuncWrapper:
    __slots__ = ('__call__',)

    def __init__(self):
        self.__call__ = None

    def set_func(self, func):
        self.__call__ = func.__call__


class FuncRecursionResolver(StubsRecursionResolver):
    def get_stub(self, request):
        return FuncWrapper()

    def saturate_stub(self, actual, stub) -> None:
        stub.set_func(actual)


class ParserFactory(BuiltinFactory):
    def __init__(
        self,
        *,
        recipe: Optional[List[Provider]] = None,
        strict_coercion: bool = True,
        debug_path: bool = True,
        default_extra: DefaultExtra = ExtraVariant.SKIP,
    ):
        super().__init__(recipe)
        self._strict_coercion = strict_coercion
        self._debug_path = debug_path
        self._default_extra = default_extra
        self._parser_cache: Dict[Any, Parser] = {}

    _provide_parser = create_factory_provision_action(ParserRequest)

    def _get_raw_config_recipe(self) -> List[Provider]:
        return [
            ConfigProvider(CfgDefaultExtra, lambda: self._default_extra),
        ]

    def _get_raw_recursion_resolving(self) -> RecursionResolving:
        return RecursionResolving(
            {ParserRequest: FuncRecursionResolver()}
        )

    def parser(self, tp: Type[T]) -> Parser[Any, T]:
        try:
            return self._parser_cache[tp]
        except KeyError:
            return self._provide_from_recipe(
                ParserRequest(
                    tp,
                    strict_coercion=self._strict_coercion,
                    debug_path=self._debug_path
                )
            )


class SerializerFactory(BuiltinFactory):
    def __init__(self, *, recipe: Optional[List[Provider]] = None, omit_default: bool = False):
        super().__init__(recipe)
        self._omit_default = omit_default

    _provide_serializer = create_factory_provision_action(SerializerRequest)

    def _get_raw_config_recipe(self) -> List[Provider]:
        return [
            ConfigProvider(CfgOmitDefault, lambda: self._omit_default),
        ]

    def _get_raw_recursion_resolving(self) -> RecursionResolving:
        return RecursionResolving(
            {SerializerRequest: FuncRecursionResolver()}
        )

    def serializer(self, tp: Type[T]) -> Serializer[T, Any]:
        return self._provide_from_recipe(SerializerRequest(tp))


# TODO: Add JsonSchemaFactory with new API
class Factory(ParserFactory, SerializerFactory):
    def __init__(
        self,
        recipe: Optional[List[Provider]] = None,
        strict_coercion: bool = True,
        debug_path: bool = True,
        default_extra: DefaultExtra = ExtraVariant.SKIP,
        omit_default: bool = False,
    ):
        ParserFactory.__init__(
            self,
            recipe=recipe,
            strict_coercion=strict_coercion,
            debug_path=debug_path,
            default_extra=default_extra
        )

        SerializerFactory.__init__(
            self,
            recipe=recipe,
            omit_default=omit_default
        )
