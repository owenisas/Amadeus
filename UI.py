import logging
import threading
import time
import json
import queue
import tkinter as tk
from tkinter import scrolledtext

# Import the existing Runner from your original module
from runner import Runner
from agent.main_agent import ActionAgent

# -- Extended Runner to support cancellation, input callback, and log agent messages --
class CancelableRunner(Runner):
    def __init__(
        self,
        audio=False,
        train=False,
        multi_agent=False,
        infinite=False,
        interactive=False,
        filters=None,
        input_callback=None,
    ):
        super().__init__(
            audio=audio,
            train=train,
            multi_agent=multi_agent,
            infinite=infinite,
            interactive=interactive,
            filters=filters,
        )
        self.stop_requested = False
        self.agent = None
        self.input_callback = input_callback

    def run(self, init_prompt):
        prompt = init_prompt
        while not self.stop_requested and prompt is not None:
            # Instantiate agent
            self.agent = ActionAgent(
                on_new_message=self.set_latest_message,
                multi_agent=self.multi_agent,
                message=prompt,
                interactive=self.interactive,
                audio=self.audio
            )
            # Monkey-patch user_interaction to UI callback
            if self.input_callback:
                setattr(self.agent, 'user_interaction', self.input_callback)

            prompt = None
            counter = 1
            while not self.stop_requested and getattr(self.agent, 'task', False):
                time.sleep(1)
                logger.info(f"Response {counter}:")
                response = self.agent.chat()
                logger.info(response)
                counter += 1
            # Get next prompt via patched user_interaction
            if not self.stop_requested and hasattr(self.agent, 'user_interaction'):
                try:
                    prompt = self.agent.user_interaction()
                except queue.Empty:
                    prompt = None

        if self.stop_requested:
            logger.info(">>> Chat canceled by user.")
        try:
            self.agent.env.end_driver()
        except Exception:
            pass

    def set_latest_message(self, msg):
        super().set_latest_message(msg)
        logger.info(f"AGENT: {msg}")

# -- Logging Handler to route logs into Tkinter Text widget --
class TextHandler(logging.Handler):
    """Sends logs to a Tkinter Text widget."""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record) + '\n'
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg)
            self.text_widget.configure(state='disabled')
            self.text_widget.yview(tk.END)
        self.text_widget.after(0, append)

# Configure root logger
logger = logging.getLogger('agent')
logger.setLevel(logging.DEBUG)
console_h = logging.StreamHandler()
console_h.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
logger.addHandler(console_h)

# -- Tkinter GUI for Runner with control buttons and input queue --
class RunnerUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Agent Runner UI")

        # Input queue for prompts
        self.input_queue = queue.Queue()

        # Output display
        self.output = scrolledtext.ScrolledText(self.root, state='disabled', wrap=tk.WORD, height=20)
        self.output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # UI logger handler
        ui_handler = TextHandler(self.output)
        ui_handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
        logger.addHandler(ui_handler)

        # Option checkboxes
        opts_frame = tk.LabelFrame(self.root, text="Runner Options")
        opts_frame.pack(fill=tk.X, padx=5, pady=5)
        self.audio_var = tk.BooleanVar(value=True)
        tk.Checkbutton(opts_frame, text="Audio", variable=self.audio_var).pack(side=tk.LEFT, padx=2)
        self.train_var = tk.BooleanVar()
        tk.Checkbutton(opts_frame, text="Train", variable=self.train_var).pack(side=tk.LEFT, padx=2)
        self.multi_var = tk.BooleanVar()
        tk.Checkbutton(opts_frame, text="Multi-Agent", variable=self.multi_var).pack(side=tk.LEFT, padx=2)
        self.infinite_var = tk.BooleanVar()
        tk.Checkbutton(opts_frame, text="Infinite", variable=self.infinite_var).pack(side=tk.LEFT, padx=2)
        self.interactive_var = tk.BooleanVar()
        tk.Checkbutton(opts_frame, text="Interactive", variable=self.interactive_var).pack(side=tk.LEFT, padx=2)

        # Filters entry
        filt_frame = tk.Frame(self.root)
        filt_frame.pack(fill=tk.X, padx=5, pady=(0,5))
        tk.Label(filt_frame, text="Filters (JSON):").pack(side=tk.LEFT)
        self.filters_var = tk.StringVar()
        tk.Entry(filt_frame, textvariable=self.filters_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Control frame: prompt entry and buttons
        ctrl_frame = tk.Frame(self.root)
        ctrl_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(ctrl_frame, text="Prompt:").pack(side=tk.LEFT)
        self.prompt_var = tk.StringVar()
        self.entry = tk.Entry(ctrl_frame, textvariable=self.prompt_var)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(ctrl_frame, text="Send", command=self.on_send).pack(side=tk.RIGHT, padx=2)
        tk.Button(ctrl_frame, text="Stop", command=self.on_stop).pack(side=tk.RIGHT)

        self.current_runner = None

    def on_send(self):
        # Determine prompt: use audio if enabled
        if self.audio_var.get():
            try:
                from audio import listen
                prompt = listen()
                logger.info(f"Recognized (audio): {prompt}")
            except Exception as e:
                logger.error(f"Audio input failed: {e}")
                return
        else:
            prompt = self.prompt_var.get().strip()
            if not prompt:
                return
        # Clear entry
        self.prompt_var.set('')

        # Load filters
        filters = None
        if self.filters_var.get().strip():
            try:
                filters = json.loads(self.filters_var.get())
            except json.JSONDecodeError as e:
                logger.error(f"Invalid filters JSON: {e}")
                return

        # If runner active, queue input
        if self.current_runner and not self.current_runner.stop_requested:
            self.input_queue.put(prompt)
            return

        # Start new runner
        runner = CancelableRunner(
            audio=self.audio_var.get(),
            train=self.train_var.get(),
            multi_agent=self.multi_var.get(),
            infinite=self.infinite_var.get(),
            interactive=self.interactive_var.get(),
            filters=filters,
            input_callback=self.input_queue.get,
        )
        self.current_runner = runner
        logger.info(f">>> USER: {prompt}")
        threading.Thread(target=self._run_agent, args=(runner, prompt), daemon=True).start()

    def on_stop(self):
        if self.current_runner:
            self.current_runner.stop_requested = True
            if getattr(self.current_runner, 'agent', None):
                try:
                    self.current_runner.agent.env.end_driver()
                except Exception:
                    pass
            logger.info(">>> Stop requested.")

    def _run_agent(self, runner, prompt):
        runner.run(prompt)
        logger.info(">>> Session complete.")

    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    app = RunnerUI()
    app.run()
