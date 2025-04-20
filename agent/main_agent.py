from client import Client


class ActionAgent:
    def __init__(self, tools_map, tools_definition, message, on_new_message: callable = None):
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
        
                    5. **When encountering Missing Personal Information (race, experience, age, etc.)**  
                       - Whenever you need personal user data or preferences that are missing, call the `call_agent` tool. Avoid providing direct guesses about user data in plain text.
                       - If the data is obtained or known, proceed with the rest of the steps (for example, clicking the correct UI element).
                       - If you need the user to clarify or provide data (such as credentials or user preferences), call a tool (like `call_agent`) as your workflow demands.
                       - Find alternative methods if the missing data is not personal information.
        
                    Additional Reminders:
                    - Remain resourceful: use the tools at your disposal to gather information, navigate the UI, and perform actions.
                """,
            },
            {
                "role": "assistant",
                "content": "Ok, I understand"
            },
            {
                "role": "user", "content": f"{message}"
            }
        ]
        open_router = "https://openrouter.ai/api/v1"
        self.client = Client(model="grok-3-beta",
                             base="https://api.x.ai/v1",
                             tools_map=tools_map,
                             tools_definition=tools_definition,
                             messages=self.messages,
                             on_new_message=on_new_message
                             )

    def chat(self):
        return self.client.chat()
