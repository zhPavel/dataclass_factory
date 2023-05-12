from typing import TypeVar

from adaptix._internal.essential import Mediator

from ...model_tools.definitions import InputShape, OutputShape
from ..model.crown_definitions import (
    BranchInpCrown,
    BranchOutCrown,
    DictExtraPolicy,
    InputNameLayout,
    InputNameLayoutRequest,
    LeafInpCrown,
    LeafOutCrown,
    OutputNameLayout,
    OutputNameLayoutRequest,
    Sieve,
)
from ..static_provider import StaticProvider, static_provision_action
from .base import ExtraMoveMaker, ExtraPoliciesMaker, PathsTo, SievesMaker, StructureMaker
from .crown_builder import InpCrownBuilder, OutCrownBuilder

T = TypeVar('T')


class BuiltinNameLayoutProvider(StaticProvider):
    def __init__(
        self,
        structure_maker: StructureMaker,
        sieves_maker: SievesMaker,
        extra_policies_maker: ExtraPoliciesMaker,
        extra_move_maker: ExtraMoveMaker,
    ):
        self._structure_maker = structure_maker
        self._sieves_maker = sieves_maker
        self._extra_policies_maker = extra_policies_maker
        self._extra_move_maker = extra_move_maker

    @static_provision_action
    def _provide_input_name_layout(self, mediator: Mediator, request: InputNameLayoutRequest) -> InputNameLayout:
        extra_move = self._extra_move_maker.make_inp_extra_move(mediator, request)
        paths_to_leaves, mapped_fields = self._structure_maker.make_inp_structure(mediator, request, extra_move)
        extra_policies = self._extra_policies_maker.make_extra_policies(
            mediator, request, paths_to_leaves, mapped_fields
        )
        return InputNameLayout(
            crown=self._create_input_crown(mediator, request.shape, paths_to_leaves, extra_policies),
            extra_move=extra_move,
        )

    # noinspection PyUnusedLocal
    def _create_input_crown(
        self,
        mediator: Mediator,
        shape: InputShape,
        path_to_leaf: PathsTo[LeafInpCrown],
        extra_policies: PathsTo[DictExtraPolicy],
    ) -> BranchInpCrown:
        return InpCrownBuilder(extra_policies).build_crown(path_to_leaf)

    @static_provision_action
    def _provide_output_name_layout(self, mediator: Mediator, request: OutputNameLayoutRequest) -> OutputNameLayout:
        extra_move = self._extra_move_maker.make_out_extra_move(mediator, request)
        paths_to_leaves, mapped_fields = self._structure_maker.make_out_structure(mediator, request, extra_move)
        path_to_sieve = self._sieves_maker.make_sieves(
            mediator, request, paths_to_leaves, mapped_fields
        )
        return OutputNameLayout(
            crown=self._create_output_crown(mediator, request.shape, paths_to_leaves, path_to_sieve),
            extra_move=extra_move,
        )

    # noinspection PyUnusedLocal
    def _create_output_crown(
        self,
        mediator: Mediator,
        shape: OutputShape,
        path_to_leaf: PathsTo[LeafOutCrown],
        path_to_sieve: PathsTo[Sieve],
    ) -> BranchOutCrown:
        return OutCrownBuilder(path_to_sieve).build_crown(path_to_leaf)
