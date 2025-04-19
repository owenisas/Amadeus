import json
import os

class History:
    def __init__(self, history_file="data/data.json"):
        self.history_file = history_file

    def read_json_file(self):
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r') as f:
                return json.load(f)
        return {}

    def append_new_data(self, new_data: dict):
        data = self.read_json_file()
        if isinstance(data, dict):
            data.update(new_data)
        elif isinstance(data, list):
            data.append(new_data)
        else:
            raise ValueError("Unsupported JSON structure.")
        with open(self.history_file, 'w') as f:
            json.dump(data, f, indent=4)
        return data
