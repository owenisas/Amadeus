from openai import OpenAI
import os
from tools.tools import Tool


class Client:
    def __init__(self, model: str, base: str, tools_map: dict, tools_definition: list, messages: list):
        self.client = OpenAI(
            api_key=os.environ['API_KEY'], base_url=base
        )
        self.model = model
        self.messages = messages
        self.tools = Tool(tools_map, tools_definition, self.messages)

    def chat(self):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=self.tools.definition,
            tool_choice="auto"

        )
        print(response)
        if not response or not response.choices:
            print("No choices returned. Possibly refusal or error.")
            return None, None
        if response.choices[0].message != '':
            self.messages.append(response.choices[0].message)
            print(response.choices[0].message.content)
        self.tools.tool_call(response.choices[0].message)
        with open("test.txt", "w", encoding="utf-8") as f:
            f.write(str(self.messages))
        return self.messages
