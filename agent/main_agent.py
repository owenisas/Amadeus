import os

from client import Client
from environment.Android import Android
import base64
from openai import OpenAI


def image_bytes_to_data_url(image_bytes, mime_type="image/png"):
    """
    Convert image bytes to a data URL.
    """
    base64_encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{base64_encoded}"


def tools_definition() -> list:
    import json
    with open(r"C:\Users\thoma\PycharmProjects\Salieri\tools\main_agent_tools.json", 'r', encoding='utf-8') as f:
        # 2. Parse the JSON into a Python object
        return json.load(f)


class ActionAgent():
    def __init__(self, message, on_new_message: callable = None, multi_agent: bool = False, infinite: bool = False,
                 filters=None, interactive: bool = False, audio: bool = False):
        self.messages = [
            {
                "role": "system",
                "content": """
                 Your mission:
                    1. **Interpret the User’s Goal**  
                       - Understand what the user wants to accomplish.
                       - Specifically, determine which UI element should be clicked based on the provided image.
        
                    2. **Devise a Strategy to Complete the Task**  
                       - If you can find a direct way to accomplish the task on the current screen, do so.
                       - Analyze the provided screenshot to identify the target UI element.
                       - If the necessary UI elements or features are not visible on the current screen, explore alternative approaches:
                         - Switch to a different screen or tab within the same app.
                         - Open relevant menus or settings.
                         - If appropriate, open a different app that might achieve the same goal.
                       - Do not repeat the same actions (calling the same tools with identical arguments) repeatedly.
        
                    3. **Multi-step Execution**  
                       - Break down the user’s request into multiple steps.
                       - Keep track of your progress. If a direct path fails or an element is missing, consider trying an alternative path or another app.
                       - Continue exploring until the goal is reached or until you have exhausted all reasonable avenues.
        
                    4. **Provide Reasonable Feedback**  
                       - When you complete an action, provide a concise confirmation message to the user.
                       - If an action fails or is not found, log the attempt and move on to another approach without getting stuck in a loop.
                       - If, after trying all plausible approaches, the goal cannot be completed, explain the situation briefly.
                    Additional Reminders:
                    - Remain resourceful: use the tools at your disposal to gather information, navigate the UI, and perform actions.
                    
                    **Remember, your ultimate goal is to give what the user wants and provide the direct result in your response**
                    **DO NOT MAKE ASSUMPTIONS FOR THE RESULT, THE USER NEEDS DIRECT RESULT**
                """,
            },
            # 5. **When encountering Missing Personal Information (race, experience, age, etc.)**
            #    - Whenever you need personal user data or preferences that are missing, call the `call_agent` tool. Avoid providing direct guesses about user data in plain text.
            #    - If the data is obtained or known, proceed with the rest of the steps (for example, clicking the correct UI element).
            #    - If you need the user to clarify or provide data (such as credentials or user preferences), call a tool (like `call_agent`) as your workflow demands.
            #    - Find alternative methods if the missing data is not personal information.
            #
            {
                "role": "assistant",
                "content": "Ok, I understand"
            },
            {
                "role": "user", "content": f"{message}"
            }
        ]
        self.env = Android()
        self.tools_map = {
            "get_display_elements": self.apply_filters,
            "get_screenshot": self.get_screenshot,
            "click": self.env.click_element,
            "edit_textbox": self.env.edit_any_textbox,
            "get_apps": self.env.get_apps,
            "open_app": self.env.open_app,
            "scroll_up": self.env.scroll_up,
            "scroll_down": self.env.scroll_down,
            "go_back": self.env.go_back,
            "press_enter": self.env.press_enter
        }
        self.filters = filters
        self.tool_definition = tools_definition()
        open_router = "https://openrouter.ai/api/v1"
        self.client = Client(model="grok-3-fast-beta",
                             base="https://api.x.ai/v1",
                             tools_map=self.tools_map,
                             tools_definition=self.tool_definition,
                             messages=self.messages,
                             on_new_message=on_new_message
                             )
        self.task = True
        self.audio = audio
        if multi_agent:
            from agent.information_agent import call_agent
            self.tools_map["call_agent"] = call_agent
            self.tool_definition.append({
                "type": "function",
                "function": {
                    "name": "call_agent",
                    "description": "calls an agent that can answer informational questions, you should ask whenever you need an answer to a question",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "questions that needs to be answered"
                            }
                        },
                        "required": ["message"]
                    }
                }
            })
        if not infinite:
            self.tools_map["end_session"] = self.done
            self.tool_definition.append({
                "type": "function",
                "function": {
                    "name": "end_session",
                    "description": "end the session when the task is complete.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            })
        if interactive:
            self.tools_map["ask_user_input"] = self.user_interaction
            self.tool_definition.append({
                "type": "function",
                "function": {
                    "name": "ask_user_input",
                    "description": "Ask the user anything.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            })

    def apply_filters(self):
        return self.env.get_display_elements(filters=self.filters)

    def user_interaction(self):
        if self.audio:
            from audio import record_to_wav, transcribe_with_groq, start_stream, read
            read(self.messages[-1].content)
            pa, stream = start_stream()
            wav_path = record_to_wav(duration_s=5.0, stream=stream, pa=pa)
            print("Transcribing with Groq…")
            transcribe = transcribe_with_groq(wav_path)
            os.remove(wav_path)
            return transcribe
        else:
            user_input = input("Enter your message:")
            return user_input

    def get_screenshot(self, text):
        completion = OpenAI(
            base_url="https://api.x.ai/v1",
            api_key=os.environ["xAI_API_KEY"]
            # Replace with your actual API key
        ).chat.completions.create(
            model="grok-2-vision-latest",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Based on the screenshotL {text}"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_bytes_to_data_url(self.env.screenshot())
                            }
                        }
                    ]
                }
            ]
        )
        return completion.choices[0].message.content

    def chat(self):
        return self.client.chat()

    def done(self):
        self.task = False


if __name__ == "__main__":
    print(tools_definition())
