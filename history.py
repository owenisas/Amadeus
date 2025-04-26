import json
import os

class History:
    def __init__(self):
        self.history_file = "data/data.json"

    def read_json_file(self):
        """Read JSON data from a file."""
        if os.path.exists(str(self.history_file)):
            with open(self.history_file, 'r') as f:
                return json.load(f)
        else:
            # Return an empty dict if file doesn't exist
            return {}

    def append_new_data(self, new_data):
        """Append new data to the JSON file and update the file."""
        data = self.read_json_file()

        # If the existing data is a dictionary, update it.
        # If it's a list, append the new data.
        if isinstance(data, dict):
            data.update(new_data)
        elif isinstance(data, list):
            data.append(new_data)
        else:
            raise ValueError("Unsupported JSON structure.")

        # Write the updated data back to the file.
        with open(self.history_file, 'w') as f:
            json.dump(data, f, indent=4)

        return data
