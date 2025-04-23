from openai import OpenAI
import os
from tools.tools import Tool
from load_env import xAI

class Client:
    def __init__(
            self,
            model: str,
            base: str,
            tools_map: dict,
            tools_definition: list,
            messages: list,
            on_new_message: callable = None
    ):
        self.client = OpenAI(
            api_key=xAI,
            base_url=base
        )
        self.model = model
        self.messages = messages
        self.tools = Tool(tools_map, tools_definition, self.messages)
        # Optional callback to update latest_message before tool execution
        self._on_new_message = on_new_message

    def chat(self):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=self.tools.definition,
            tool_choice="auto",
            temperature=0.6
        )
        print(response)
        if not response or not response.choices:
            print("No choices returned. Possibly refusal or error.")
            return None

        message = response.choices[0].message
        content = message.content or ''
        if content.strip():
            # Invoke the hook so `latest_message` is updated before any tool runs
            if self._on_new_message:
                self._on_new_message(content)
            # Append the new message for context
            self.messages.append(message)
            print(content)

        # Now dispatch any tool calls (e.g., end_session) after the latest_message is set
        self.tools.tool_call(message)

        # Persist conversation for debugging
        with open("messages.txt", "w", encoding="utf-8") as f:
            f.write(str(self.messages))

        return content
