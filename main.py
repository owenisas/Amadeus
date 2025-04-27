from runner import Runner
import json

with open("filter.json", "r") as fp:
    filters = json.load(fp)

runner = Runner(filters=filters) #set audio to true enables audio input and output
Stock_Prompt = "Buy me a carpet on walmart"
runner.run(Stock_Prompt) #prompt is ignored if audio is true
