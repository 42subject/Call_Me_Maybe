import json
from enum import Enum
from typing import ClassVar, TypedDict

from pydantic import BaseModel, Field

from ..input_models import FunctionParametersModel, ParameterType


class FrameType(str, Enum):
    """
    JSON prefix validation中のコンテナ種別を表す
    """

    ARRAY = "array"
    OBJECT = "object"


class FrameState(str, Enum):
    """
    JSON prefix validation中のコンテナ内状態を表す
    """

    EXPECT_VALUE_OR_END = "expect_value_or_end"
    EXPECT_VALUE = "expect_value"
    AFTER_VALUE = "after_value"
    EXPECT_KEY_OR_END = "expect_key_or_end"
    EXPECT_KEY = "expect_key"
    AFTER_KEY = "after_key"


class FrameRole(str, Enum):
    """
    JSON prefix validation中のコンテナの役割を表す
    """

    RESPONSE = "response"
    SCHEMA_OBJECT = "schema_object"
    SCHEMA_ARRAY = "schema_array"
    NORMAL = "normal"


class JsonFrame(TypedDict):
    """
    JSON prefix validation中のスタックフレームを表す
    """

    type: FrameType
    state: FrameState
    role: FrameRole
    key_index: int
    current_key: str
    properties: dict[str, FunctionParametersModel]
    items: FunctionParametersModel | None
    seen_keys: set[str]


class JsonValidator(BaseModel):
    """
    生成中の文字列が期待するJSON形式のprefixとして有効かを判定する
    """

    RESPONSE_KEYS: ClassVar[tuple[str, ...]] = (
        "prompt",
        "name",
        "parameters",
    )
    function_names: tuple[str, ...] = ()
    function_parameters: dict[str, dict[str, FunctionParametersModel]] = Field(
        default_factory=dict
    )
    expected_prompt: str = ""
    text: str = ""

    def reset(self) -> None:
        """
        検証中のJSON文字列を空に戻す
        """
        self.text = ""

    def is_valid_string(self, text: str) -> bool:
        """
        文字列を追加してもJSON prefixとして有効かを判定する

        Args:
            text: 追加候補の文字列

        Returns:
            bool: 追加後も有効なJSON prefixならTrue
        """
        next_text = self.text + text
        if not self._is_valid_json_prefix(next_text):
            return False
        self.text = next_text
        return True

    def is_complete(self) -> bool:
        """
        現在の文字列が完全なJSONとして読み込めるかを判定する

        Returns:
            bool: 完全なJSONならTrue
        """
        try:
            json.loads(self.text)
        except json.JSONDecodeError:
            return False
        return True

    def _is_valid_json_prefix(self, text: str) -> bool:
        """
        文字列が期待するJSON形式のprefixとして有効かを判定する

        Args:
            text: 判定する文字列

        Returns:
            bool: 有効なJSON prefixならTrue
        """
        stack: list[JsonFrame] = []
        state = {"mode": "start"}
        string_kind = ""
        key_buffer = ""
        value_buffer = ""
        literal = ""
        literal_index = 0
        number_state = ""
        escape = False
        unicode_escape_count = 0
        index = 0
        selected_function_name = ""

        def build_frame(
            frame_type: FrameType,
            state_name: FrameState,
            role: FrameRole,
            properties: dict[str, FunctionParametersModel] | None = None,
            items: FunctionParametersModel | None = None,
        ) -> JsonFrame:
            return {
                "type": frame_type,
                "state": state_name,
                "role": role,
                "key_index": 0,
                "current_key": "",
                "properties": properties or {},
                "items": items,
                "seen_keys": set(),
            }

        def is_hex(char: str) -> bool:
            return (
                "0" <= char <= "9"
                or "a" <= char <= "f"
                or "A" <= char <= "F"
            )

        def value_finished() -> None:
            if not stack:
                state["mode"] = "after_end"
                return
            frame = stack[-1]
            frame["state"] = FrameState.AFTER_VALUE
            if frame["role"] == FrameRole.RESPONSE:
                frame["key_index"] += 1
            state["mode"] = "normal"

        def start_value(char: str) -> bool:
            nonlocal string_kind, value_buffer, literal
            nonlocal literal_index, number_state
            expected_schema = get_expected_schema()
            match char:
                case '"':
                    if (
                        expected_schema is not None
                        and expected_schema.type != ParameterType.STR
                    ):
                        return False
                    state["mode"] = "string"
                    string_kind = "value"
                    value_buffer = ""
                    return True
                case "{":
                    if is_parameters_value():
                        parameters = self.function_parameters.get(
                            selected_function_name,
                            {},
                        )
                        stack.append(
                            build_frame(
                                FrameType.OBJECT,
                                FrameState.EXPECT_KEY_OR_END,
                                FrameRole.SCHEMA_OBJECT,
                                parameters,
                            )
                        )
                    elif expected_schema is not None:
                        if expected_schema.type != ParameterType.OBJECT:
                            return False
                        stack.append(
                            build_frame(
                                FrameType.OBJECT,
                                FrameState.EXPECT_KEY_OR_END,
                                FrameRole.SCHEMA_OBJECT,
                                expected_schema.properties,
                            )
                        )
                    else:
                        role = (
                            FrameRole.RESPONSE
                            if not stack
                            else FrameRole.NORMAL
                        )
                        stack.append(
                            build_frame(
                                FrameType.OBJECT,
                                FrameState.EXPECT_KEY_OR_END,
                                role,
                            )
                        )
                    state["mode"] = "normal"
                    return True
                case "[":
                    if expected_schema is not None:
                        if expected_schema.type != ParameterType.ARRAY:
                            return False
                        stack.append(
                            build_frame(
                                FrameType.ARRAY,
                                FrameState.EXPECT_VALUE_OR_END,
                                FrameRole.SCHEMA_ARRAY,
                                items=expected_schema.items,
                            )
                        )
                    else:
                        stack.append(
                            build_frame(
                                FrameType.ARRAY,
                                FrameState.EXPECT_VALUE_OR_END,
                                FrameRole.NORMAL,
                            )
                        )
                    state["mode"] = "normal"
                    return True
                case "t":
                    if (
                        expected_schema is not None
                        and expected_schema.type != ParameterType.BOOLEAN
                    ):
                        return False
                    state["mode"] = "literal"
                    literal = "true"
                    literal_index = 1
                    return True
                case "f":
                    if (
                        expected_schema is not None
                        and expected_schema.type != ParameterType.BOOLEAN
                    ):
                        return False
                    state["mode"] = "literal"
                    literal = "false"
                    literal_index = 1
                    return True
                case "n":
                    if (
                        expected_schema is not None
                        and expected_schema.type != ParameterType.NULL
                    ):
                        return False
                    state["mode"] = "literal"
                    literal = "null"
                    literal_index = 1
                    return True
                case "-":
                    if (
                        expected_schema is not None
                        and expected_schema.type
                        not in {ParameterType.NUMBER, ParameterType.INTEGER}
                    ):
                        return False
                    state["mode"] = "number"
                    number_state = "after_minus"
                    return True
                case "0":
                    if (
                        expected_schema is not None
                        and expected_schema.type
                        not in {ParameterType.NUMBER, ParameterType.INTEGER}
                    ):
                        return False
                    state["mode"] = "number"
                    number_state = "int_zero"
                    return True
                case _ if "1" <= char <= "9":
                    if (
                        expected_schema is not None
                        and expected_schema.type
                        not in {ParameterType.NUMBER, ParameterType.INTEGER}
                    ):
                        return False
                    state["mode"] = "number"
                    number_state = "int_digits"
                    return True
                case _:
                    return False

        def expected_response_key(frame: JsonFrame) -> str | None:
            if frame["role"] != FrameRole.RESPONSE:
                return None
            if frame["key_index"] >= len(self.RESPONSE_KEYS):
                return None
            return self.RESPONSE_KEYS[frame["key_index"]]

        def is_name_value() -> bool:
            if not stack:
                return False
            frame = stack[-1]
            return (
                frame["type"] == FrameType.OBJECT
                and frame["role"] == FrameRole.RESPONSE
                and frame["current_key"] == "name"
            )

        def is_prompt_value() -> bool:
            if not stack:
                return False
            frame = stack[-1]
            return (
                frame["type"] == FrameType.OBJECT
                and frame["role"] == FrameRole.RESPONSE
                and frame["current_key"] == "prompt"
            )

        def is_parameters_value() -> bool:
            if not stack:
                return False
            frame = stack[-1]
            return (
                frame["type"] == FrameType.OBJECT
                and frame["role"] == FrameRole.RESPONSE
                and frame["current_key"] == "parameters"
            )

        def append_response_value(char: str) -> bool:
            nonlocal value_buffer
            if not is_prompt_value() and not is_name_value():
                return True
            value_buffer += char
            if (
                is_prompt_value()
                and self.expected_prompt
                and not self.expected_prompt.startswith(value_buffer)
            ):
                return False
            if (
                is_name_value()
                and not is_valid_function_name_prefix(value_buffer)
            ):
                return False
            return True

        def get_expected_schema() -> FunctionParametersModel | None:
            if not stack:
                return None
            frame = stack[-1]
            if (
                frame["role"] == FrameRole.SCHEMA_OBJECT
                and frame["state"] == FrameState.EXPECT_VALUE
            ):
                return frame["properties"].get(frame["current_key"])
            if (
                frame["role"] == FrameRole.SCHEMA_ARRAY
                and frame["state"] in {
                    FrameState.EXPECT_VALUE_OR_END,
                    FrameState.EXPECT_VALUE,
                }
            ):
                return frame["items"]
            return None

        def is_valid_function_name_prefix(value: str) -> bool:
            if not self.function_names:
                return True
            return any(
                function_name.startswith(value)
                for function_name in self.function_names
            )

        def expected_schema_key(frame: JsonFrame) -> str | None:
            if frame["role"] != FrameRole.SCHEMA_OBJECT:
                return None
            candidates = [
                key for key in frame["properties"]
                if key not in frame["seen_keys"]
            ]
            for key in candidates:
                if key == key_buffer:
                    return key
            return None

        def is_valid_schema_key_prefix(frame: JsonFrame, value: str) -> bool:
            if frame["role"] != FrameRole.SCHEMA_OBJECT:
                return True
            return any(
                key.startswith(value)
                for key in frame["properties"]
                if key not in frame["seen_keys"]
            )

        def has_all_schema_keys(frame: JsonFrame) -> bool:
            if frame["role"] != FrameRole.SCHEMA_OBJECT:
                return True
            return frame["seen_keys"] == set(frame["properties"])

        def finish_container(char: str) -> bool:
            if not stack:
                return False
            frame = stack.pop()
            if (
                frame["type"] == FrameType.ARRAY
                and char == "]"
                and frame["state"] in {
                    FrameState.EXPECT_VALUE_OR_END,
                    FrameState.AFTER_VALUE,
                }
            ):
                value_finished()
                return True
            if (
                frame["type"] == FrameType.OBJECT
                and char == "}"
                and frame["state"] in {
                    FrameState.EXPECT_KEY_OR_END,
                    FrameState.AFTER_VALUE,
                }
                and has_all_schema_keys(frame)
                and (
                    frame["role"] != FrameRole.RESPONSE
                    or frame["key_index"] == len(self.RESPONSE_KEYS)
                )
            ):
                value_finished()
                return True
            return False

        def is_complete_number() -> bool:
            if is_integer_value():
                return number_state in {
                    "int_zero",
                    "int_digits",
                }
            return number_state in {
                "int_zero",
                "int_digits",
                "frac_digits",
                "exp_digits",
            }

        def is_integer_value() -> bool:
            expected_schema = get_expected_schema()
            return (
                expected_schema is not None
                and expected_schema.type == ParameterType.INTEGER
            )

        def consume_number_char(char: str) -> bool:
            nonlocal number_state
            match number_state:
                case "after_minus":
                    if char == "0":
                        number_state = "int_zero"
                        return True
                    if "1" <= char <= "9":
                        number_state = "int_digits"
                        return True
                    return False
                case "int_zero":
                    if is_integer_value():
                        return False
                    if char == ".":
                        number_state = "frac_start"
                        return True
                    if char in {"e", "E"}:
                        number_state = "exp_start"
                        return True
                    return False
                case "int_digits":
                    if char.isdigit():
                        return True
                    if is_integer_value():
                        return False
                    if char == ".":
                        number_state = "frac_start"
                        return True
                    if char in {"e", "E"}:
                        number_state = "exp_start"
                        return True
                    return False
                case "frac_start":
                    if char.isdigit():
                        number_state = "frac_digits"
                        return True
                    return False
                case "frac_digits":
                    if char.isdigit():
                        return True
                    if char in {"e", "E"}:
                        number_state = "exp_start"
                        return True
                    return False
                case "exp_start":
                    if char in {"+", "-"}:
                        number_state = "exp_sign"
                        return True
                    if char.isdigit():
                        number_state = "exp_digits"
                        return True
                    return False
                case "exp_sign":
                    if char.isdigit():
                        number_state = "exp_digits"
                        return True
                    return False
                case "exp_digits":
                    return char.isdigit()
                case _:
                    return False

        while index < len(text):
            char = text[index]
            mode = state["mode"]

            match mode:
                case "string":
                    if unicode_escape_count > 0:
                        if not is_hex(char):
                            return False
                        unicode_escape_count -= 1
                        escape = unicode_escape_count > 0
                    elif escape:
                        match char:
                            case "u":
                                unicode_escape_count = 4
                            case (
                                '"'
                                | "\\"
                                | "/"
                                | "b"
                                | "f"
                                | "n"
                                | "r"
                                | "t"
                            ):
                                escaped_chars = {
                                    '"': '"',
                                    "\\": "\\",
                                    "/": "/",
                                    "b": "\b",
                                    "f": "\f",
                                    "n": "\n",
                                    "r": "\r",
                                    "t": "\t",
                                }
                                if not append_response_value(
                                    escaped_chars[char],
                                ):
                                    return False
                            case _:
                                return False
                        escape = unicode_escape_count > 0
                    elif char == "\\":
                        escape = True
                    elif char == '"':
                        if string_kind == "key":
                            frame = stack[-1]
                            expected_key = expected_response_key(frame)
                            if (
                                expected_key is not None
                                and key_buffer != expected_key
                            ):
                                return False
                            if (
                                frame["role"] == FrameRole.SCHEMA_OBJECT
                                and expected_schema_key(frame) is None
                            ):
                                return False
                            if frame["role"] == FrameRole.SCHEMA_OBJECT:
                                frame["seen_keys"].add(key_buffer)
                            frame["current_key"] = key_buffer
                            stack[-1]["state"] = FrameState.AFTER_KEY
                            state["mode"] = "normal"
                        else:
                            if (
                                is_name_value()
                                and self.function_names
                                and value_buffer not in self.function_names
                            ):
                                return False
                            if is_name_value():
                                selected_function_name = value_buffer
                            if (
                                is_prompt_value()
                                and self.expected_prompt
                                and value_buffer != self.expected_prompt
                            ):
                                return False
                            value_finished()
                    elif string_kind == "key":
                        key_buffer += char
                        expected_key = expected_response_key(stack[-1])
                        if (
                            expected_key is not None
                            and not expected_key.startswith(key_buffer)
                        ):
                            return False
                        if not is_valid_schema_key_prefix(
                            stack[-1],
                            key_buffer,
                        ):
                            return False
                    elif ord(char) < 0x20:
                        return False
                    elif not append_response_value(char):
                        return False
                    index += 1
                    continue

                case "literal":
                    if (
                        literal_index >= len(literal)
                        or char != literal[literal_index]
                    ):
                        return False
                    literal_index += 1
                    if literal_index == len(literal):
                        value_finished()
                    index += 1
                    continue

                case "number":
                    if consume_number_char(char):
                        index += 1
                        continue
                    if char.isspace() or char in {",", "]", "}"}:
                        if not is_complete_number():
                            return False
                        value_finished()
                        continue
                    return False

            if char.isspace():
                index += 1
                continue

            match mode:
                case "start":
                    if char != "{" or not start_value(char):
                        return False
                    index += 1
                    continue
                case "after_end":
                    return False

            if not stack:
                return False

            frame = stack[-1]
            match frame["type"]:
                case FrameType.ARRAY:
                    match frame["state"]:
                        case FrameState.EXPECT_VALUE_OR_END:
                            if char == "]":
                                if not finish_container(char):
                                    return False
                            elif not start_value(char):
                                return False
                        case FrameState.EXPECT_VALUE:
                            if not start_value(char):
                                return False
                        case FrameState.AFTER_VALUE:
                            match char:
                                case ",":
                                    frame["state"] = FrameState.EXPECT_VALUE
                                case "]":
                                    if not finish_container(char):
                                        return False
                                case _:
                                    return False
                        case _:
                            return False
                case _:
                    match frame["state"]:
                        case FrameState.EXPECT_KEY_OR_END:
                            match char:
                                case "}":
                                    if not finish_container(char):
                                        return False
                                case '"':
                                    state["mode"] = "string"
                                    string_kind = "key"
                                    key_buffer = ""
                                case _:
                                    return False
                        case FrameState.EXPECT_KEY:
                            if char != '"':
                                return False
                            state["mode"] = "string"
                            string_kind = "key"
                            key_buffer = ""
                        case FrameState.AFTER_KEY:
                            if char != ":":
                                return False
                            frame["state"] = FrameState.EXPECT_VALUE
                        case FrameState.EXPECT_VALUE:
                            if not start_value(char):
                                return False
                        case FrameState.AFTER_VALUE:
                            match char:
                                case ",":
                                    if (
                                        frame["role"] == FrameRole.RESPONSE
                                        and frame["key_index"]
                                        >= len(self.RESPONSE_KEYS)
                                    ):
                                        return False
                                    frame["state"] = FrameState.EXPECT_KEY
                                case "}":
                                    if not finish_container(char):
                                        return False
                                case _:
                                    return False
                        case _:
                            return False

            index += 1

        return True
