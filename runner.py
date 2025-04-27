import time

from agent.main_agent import ActionAgent


class Runner:
    def __init__(self, audio: bool = False, train: bool = False, multi_agent: bool = False, infinite: bool = False,
                 interactive: bool = False, filters: dict = None):
        self.latest_msg = ''
        self.audio = audio
        self.train = train
        self.multi_agent = multi_agent
        self.infinite = infinite
        self.interactive = interactive
        self.filters = filters

    def run(self, init_prompt):
        if self.train:
            from ML.data import log_click_csv
        if self.audio:
            from audio import listen
            user_request = listen()
            print(user_request)
            agent = ActionAgent(on_new_message=self.set_latest_message, multi_agent=self.multi_agent,
                                message=user_request, interactive=self.interactive, audio=self.audio,
                                filters=self.filters)
        else:
            agent = ActionAgent(on_new_message=self.set_latest_message, multi_agent=self.multi_agent,
                                message=init_prompt, interactive=self.interactive, filters=self.filters)
        i = 1
        while agent.task:
            time.sleep(1)
            print(f"Response{i}:")
            response = agent.chat()
            i += 1
        if self.audio:
            from audio import read
            read(self.latest_msg)
        agent.env.end_driver()

    def set_latest_message(self, msg):
        self.latest_msg = msg
