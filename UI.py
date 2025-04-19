import tkinter as tk

# Global variable to hold the conversation messages
messages = []


def submit_input():
    # Retrieve user input from the text widget.
    user_text = text_input.get("1.0", tk.END).strip()
    if user_text:
        # Replace the default message with the user's message.
        global messages
        messages = [{"role": "user", "content": user_text}]
        output_label.config(text=f"Message set: {messages}")
        # Optionally, you could now send `messages` to your LLM API call.
    else:
        output_label.config(text="Please enter a message.")


# Create the main application window.
root = tk.Tk()
root.title("LLM Assistant Input")

# Create a frame for better organization.
frame = tk.Frame(root, padx=10, pady=10)
frame.pack()

# Label prompting for user input.
label = tk.Label(frame, text="Enter your message:")
label.pack()

# Text widget for multi-line input.
text_input = tk.Text(frame, height=5, width=50)
text_input.pack()

# Submit button that triggers the submit_input function.
submit_button = tk.Button(frame, text="Submit", command=submit_input)
submit_button.pack(pady=5)

# Label to show feedback or the new message.
output_label = tk.Label(frame, text="", fg="green")
output_label.pack()

# Start the tkinter main event loop.
root.mainloop()
