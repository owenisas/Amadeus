from mem0.proxy.main import Mem0
import os
from openai import OpenAI
from load_env import xAI

base_url = "https://api.x.ai/v1",
config = {
    "llm": {
        "provider": "xai",
        "config": {
            "model": "grok-2-latest",
            "temperature": 0.1,
            "max_tokens": 2000,
        }
    }
}

client = OpenAI(
    api_key=xAI,
    base_url="https://api.x.ai/v1",
)
#os.environ['OPENAI_API_KEY'] = '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'

# Memory saved after this will look like: "Loves Indian food. Allergic to cheese and cannot eat pizza."

# Second interaction: Leveraging stored memory
messages = [
    {
        "role": "system",
        "content": """
        The user will instuct you to perform a task.
        You will be shown a screen as well as relevant interactable elements and you will be given a set of tools to use to perform the task.
        you should remember information about the user, if a certain information is not available, you should generate one and remember that,
        You should then reason about what needs to be done to complete the task, putting your thoughts in <opinion></opinion> tags.
        You should then use the tools to perform the task, putting the tool calls in <tool_call></tool_call> tags.
        """,
    },
    {
        "role": "assistant",
        "content": "Ok, I understand"
    },
]
user_id = "Survey Taker"
chat_completion = client.chat.completions.create(
    messages=messages,
    model="grok-2-latest",
)
print(chat_completion.choices[0].message.content)
# Answer: You might enjoy Indian restaurants in San Francisco, such as Amber India, Dosa, or Curry Up Now, which offer delicious options without cheese.
