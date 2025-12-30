from openai import OpenAI
import os
from tools.tools import Tool
from config import APIConfig, AgentConfig


class Client:
    def __init__(
            self,
            model: str = None,
            base: str = None,
            tools_map: dict = None,
            tools_definition: list = None,
            messages: list = None,
            on_new_message: callable = None,
            api_key: str = None,
            temperature: float = None
    ):
        # Use provided values or fall back to config defaults
        key = api_key or APIConfig.get_api_key()
        base_url = base or APIConfig.get_base_url()

        self.client = OpenAI(
            api_key=key,
            base_url=base_url
        )
        self.model = model
        self.messages = messages or []
        self.temperature = temperature or AgentConfig.TEMPERATURE

        if tools_map and tools_definition:
            self.tools = Tool(tools_map, tools_definition, self.messages)
        else:
            self.tools = None

        # Optional callback to update latest_message before tool execution
        self._on_new_message = on_new_message

    def chat(self):
        kwargs = {
            "model": self.model,
            "messages": self.messages,
            "temperature": self.temperature,
        }

        # Only include tools if they exist
        if self.tools:
            kwargs["tools"] = self.tools.definition
            kwargs["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**kwargs)
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
        if self.tools:
            self.tools.tool_call(message)

        # Persist conversation for debugging
        with open("messages.txt", "w", encoding="utf-8") as f:
            f.write(str(self.messages))

        return content
