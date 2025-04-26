from openai import OpenAI
from history import History
import json
from load_env import xAI

history = History()
tools_definition2 = [
    {
        "type": "function",
        "function": {
            "name": "add_new_data",
            "description": "Updates the JSON file with new values.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "dict",
                        "description": "the data dict to update"
                    }
                },
                "required": ["data"]
            }
        }
    },
]


def add_new_data(data):
    history.append_new_data(new_data=data)


tools_map2 = {
    "add_new_data": add_new_data
}
client = OpenAI(
    api_key=xAI,
    base_url="https://api.x.ai/v1"
)


def request_agent(text: str):
    messages2 = [
        {
            "role": "system",
            "content": f"""
            Below is a user's profile in JSON format:
            {history.read_json_file()}       
            When the user asks a question, follow these rules:
            1. If it is a multiple-choice question (e.g., "choose from [A, B, C]"), 
               return ONLY the chosen option—nothing else.
            2. If it is an open-ended question, respond with a short, direct answer (one or two sentences).
            3. After you decide on your answer or option, provide the JSON key and value
               in the format needed to update it through the 'add_new_data' tool. 
               - Example: If you decide the user lives in a 'Suburban' area, your response might 
                 show the text "Suburban" and then update JSON with "area type": "Suburban".
            4. Do not provide any extra commentary or explanations beyond these steps.

            If the provided JSON lacks sufficient data to answer the question 
            (for example, if the "age" field is missing or invalid),
            you should generate a realistic answer or value that fits one of the options
            or can answer the question. 

            Remember: your final output must contain:
            - The single chosen option or short open-ended answer.
            - The JSON key-value pair to pass to 'add_new_data'.

            For example, if asked: "Which area type best describes where you live? 
            Please choose from Urban, Suburban, or Rural?", your answer might be:

            Suburban
            "area type": "Suburban"
            """,
        },
        {
            "role": "user", "content": f"question:{text}"
        }
    ]
    response2 = client.chat.completions.create(
        model="grok-3-beta",
        messages=messages2,
        tools=tools_definition2,
        tool_choice="auto"  # Let the model decide if a tool call is needed
    )
    return response2


def call_agent(message):
    text = message
    response = request_agent(
        text=text)
    if hasattr(response.choices[0].message, "tool_calls") and response.choices[0].message.tool_calls:
        for tool_call in response.choices[0].message.tool_calls:
            function_name = tool_call.function.name
            # Parse the JSON arguments if provided.
            function_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
            print(f"Executing tool call: {function_name} with args: {function_args}")
            tools_map2[function_name](**function_args)

    print(response.choices[0].message.content)
    return response.choices[0].message.content
