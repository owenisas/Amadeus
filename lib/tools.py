import json

class Tool:
    def __init__(self, tool_map: dict, tool_definition: list, messages: list):
        self.name = "tool"
        self.map = tool_map
        self.definition = tool_definition
        self.messages = messages

    def tool_call(self, message):
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                print(f"Executing tool call: {function_name} with args: {function_args}")
                result = self.map[function_name](**function_args)
                print(result)
                self.messages.append({
                    "role": "tool",
                    "content": json.dumps(result),
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name
                })
