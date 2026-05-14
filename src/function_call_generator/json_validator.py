import json


class JsonValidator:
    def __init__(self) -> None:
        self.text = ""

    def is_valid_string(self, text: str) -> bool:
        next_text = self.text + text
        if not self._is_valid_json_prefix(next_text):
            return False
        self.text = next_text
        return True

    def is_complete(self) -> bool:
        try:
            json.loads(self.text)
        except json.JSONDecodeError:
            return False
        return True

    def _is_valid_json_prefix(self, text: str) -> bool:
        stack: list[dict[str, str]] = []
        state = {"mode": "start"}
        string_kind = ""
        literal = ""
        literal_index = 0
        number_state = ""
        escape = False
        unicode_escape_count = 0
        index = 0

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
            stack[-1]["state"] = "after_value"
            state["mode"] = "normal"

        def start_value(char: str) -> bool:
            nonlocal string_kind, literal, literal_index, number_state
            if char == '"':
                state["mode"] = "string"
                string_kind = "value"
                return True
            if char == "{":
                stack.append({"type": "object", "state": "expect_key_or_end"})
                state["mode"] = "normal"
                return True
            if char == "[":
                stack.append({"type": "array", "state": "expect_value_or_end"})
                state["mode"] = "normal"
                return True
            if char == "t":
                state["mode"] = "literal"
                literal = "true"
                literal_index = 1
                return True
            if char == "f":
                state["mode"] = "literal"
                literal = "false"
                literal_index = 1
                return True
            if char == "n":
                state["mode"] = "literal"
                literal = "null"
                literal_index = 1
                return True
            if char == "-":
                state["mode"] = "number"
                number_state = "after_minus"
                return True
            if char == "0":
                state["mode"] = "number"
                number_state = "int_zero"
                return True
            if "1" <= char <= "9":
                state["mode"] = "number"
                number_state = "int_digits"
                return True
            return False

        def finish_container(char: str) -> bool:
            if not stack:
                return False
            frame = stack.pop()
            if (
                frame["type"] == "array"
                and char == "]"
                and frame["state"] in {"expect_value_or_end", "after_value"}
            ):
                value_finished()
                return True
            if (
                frame["type"] == "object"
                and char == "}"
                and frame["state"] in {"expect_key_or_end", "after_value"}
            ):
                value_finished()
                return True
            return False

        def is_complete_number() -> bool:
            return number_state in {
                "int_zero",
                "int_digits",
                "frac_digits",
                "exp_digits",
            }

        def consume_number_char(char: str) -> bool:
            nonlocal number_state
            if number_state == "after_minus":
                if char == "0":
                    number_state = "int_zero"
                    return True
                if "1" <= char <= "9":
                    number_state = "int_digits"
                    return True
                return False
            if number_state == "int_zero":
                if char == ".":
                    number_state = "frac_start"
                    return True
                if char in {"e", "E"}:
                    number_state = "exp_start"
                    return True
                return False
            if number_state == "int_digits":
                if char.isdigit():
                    return True
                if char == ".":
                    number_state = "frac_start"
                    return True
                if char in {"e", "E"}:
                    number_state = "exp_start"
                    return True
                return False
            if number_state == "frac_start":
                if char.isdigit():
                    number_state = "frac_digits"
                    return True
                return False
            if number_state == "frac_digits":
                if char.isdigit():
                    return True
                if char in {"e", "E"}:
                    number_state = "exp_start"
                    return True
                return False
            if number_state == "exp_start":
                if char in {"+", "-"}:
                    number_state = "exp_sign"
                    return True
                if char.isdigit():
                    number_state = "exp_digits"
                    return True
                return False
            if number_state == "exp_sign":
                if char.isdigit():
                    number_state = "exp_digits"
                    return True
                return False
            if number_state == "exp_digits":
                return char.isdigit()
            return False

        while index < len(text):
            char = text[index]
            mode = state["mode"]

            if mode == "string":
                if unicode_escape_count > 0:
                    if not is_hex(char):
                        return False
                    unicode_escape_count -= 1
                    escape = unicode_escape_count > 0
                elif escape:
                    if char == "u":
                        unicode_escape_count = 4
                    elif char not in {'"', "\\", "/", "b", "f", "n", "r", "t"}:
                        return False
                    escape = unicode_escape_count > 0
                elif char == "\\":
                    escape = True
                elif char == '"':
                    if string_kind == "key":
                        stack[-1]["state"] = "after_key"
                        state["mode"] = "normal"
                    else:
                        value_finished()
                elif ord(char) < 0x20:
                    return False
                index += 1
                continue

            if mode == "literal":
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

            if mode == "number":
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

            if mode == "start":
                if not start_value(char):
                    return False
                index += 1
                continue

            if mode == "after_end":
                return False

            if not stack:
                return False

            frame = stack[-1]
            if frame["type"] == "array":
                if frame["state"] == "expect_value_or_end":
                    if char == "]":
                        if not finish_container(char):
                            return False
                    elif not start_value(char):
                        return False
                elif frame["state"] == "expect_value":
                    if not start_value(char):
                        return False
                elif frame["state"] == "after_value":
                    if char == ",":
                        frame["state"] = "expect_value"
                    elif char == "]":
                        if not finish_container(char):
                            return False
                    else:
                        return False
                else:
                    return False
            else:
                if frame["state"] == "expect_key_or_end":
                    if char == "}":
                        if not finish_container(char):
                            return False
                    elif char == '"':
                        state["mode"] = "string"
                        string_kind = "key"
                    else:
                        return False
                elif frame["state"] == "expect_key":
                    if char != '"':
                        return False
                    state["mode"] = "string"
                    string_kind = "key"
                elif frame["state"] == "after_key":
                    if char != ":":
                        return False
                    frame["state"] = "expect_value"
                elif frame["state"] == "expect_value":
                    if not start_value(char):
                        return False
                elif frame["state"] == "after_value":
                    if char == ",":
                        frame["state"] = "expect_key"
                    elif char == "}":
                        if not finish_container(char):
                            return False
                    else:
                        return False
                else:
                    return False

            index += 1

        return True
