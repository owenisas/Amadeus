"""
Runner module for Amadeus - orchestrates agent execution.
"""

import time

from agent.main_agent import ActionAgent
from agent.vision_agent import VisionAgent


class Runner:
    """
    Runs Amadeus agents in a loop until task completion.
    
    Supports two agent modes:
    - ActionAgent: Uses UI element tree + vision (default, more reliable)
    - VisionAgent: Pure vision mode, only uses screenshots and coordinates
    """
    
    def __init__(
        self, 
        audio: bool = False, 
        train: bool = False, 
        multi_agent: bool = False, 
        infinite: bool = False,
        interactive: bool = False, 
        filters: dict = None,
        vision_mode: bool = False
    ):
        self.latest_msg = ''
        self.audio = audio
        self.train = train
        self.multi_agent = multi_agent
        self.infinite = infinite
        self.interactive = interactive
        self.filters = filters
        self.vision_mode = vision_mode

    def run(self, init_prompt: str):
        """
        Run the agent with the given prompt.
        
        Args:
            init_prompt: The task/prompt for the agent to execute
        """
        if self.train:
            from ML.data import log_click_csv
        
        # Get user input via audio if enabled
        if self.audio:
            from audio import listen
            user_request = listen()
            print(f"Voice input: {user_request}")
            prompt = user_request
        else:
            prompt = init_prompt
        
        # Create the appropriate agent based on mode
        if self.vision_mode:
            print("\n🔍 Running in VISION MODE (pure visual understanding)")
            agent = VisionAgent(
                message=prompt,
                on_new_message=self.set_latest_message,
                infinite=self.infinite,
                interactive=self.interactive,
                audio=self.audio
            )
        else:
            print("\n🎯 Running in ACTION MODE (UI tree + vision)")
            agent = ActionAgent(
                message=prompt,
                on_new_message=self.set_latest_message,
                multi_agent=self.multi_agent,
                infinite=self.infinite,
                interactive=self.interactive,
                audio=self.audio,
                filters=self.filters
            )
        
        # Run agent loop
        iteration = 1
        max_iterations = 50  # Safety limit
        
        while agent.task and iteration <= max_iterations:
            time.sleep(0.5)  # Small delay between iterations
            print(f"\n--- Step {iteration} ---")
            
            try:
                response = agent.chat()
                if response:
                    print(f"Agent: {response[:200]}..." if len(str(response)) > 200 else f"Agent: {response}")
            except Exception as e:
                print(f"Error in step {iteration}: {e}")
                break
            
            iteration += 1
        
        if iteration > max_iterations:
            print(f"\n⚠️ Reached maximum iterations ({max_iterations})")
        
        # Read final message aloud if audio enabled
        if self.audio and self.latest_msg:
            from audio import read
            read(self.latest_msg)
        
        # Cleanup
        print("\n✅ Session complete")
        agent.env.end_driver()

    def set_latest_message(self, msg: str):
        """Callback to capture the latest agent message."""
        self.latest_msg = msg
