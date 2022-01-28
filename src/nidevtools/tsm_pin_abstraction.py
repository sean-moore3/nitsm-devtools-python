import nitsm.codemoduleapi
import nitsm.enums
import nitsm.pinquerycontexts
import nidaqmx.constants
import enum
import typing


# Types Definition
PinsArg = typing.Union[str, typing.Sequence[str]]
Any = typing.Any
StringTuple = typing.Tuple[str]


def pin_query_context_to_channel(pin_query_context: nitsm.pinquerycontexts.PinQueryContext):
    pin_query_context.publish()
