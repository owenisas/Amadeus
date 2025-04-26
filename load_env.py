from dotenv import load_dotenv
import os
# look for .env in the current working directory

load_dotenv()

# now you can access your vars via os.environ
xAI = os.environ.get("xAI_API_KEY")
open_router_API = os.environ.get("open_router_API")
groq_API = os.environ.get("groq_API")
pvporcupine_win_API = os.environ.get("pvporcupine_win_API")
pvporcupine_mac_API = os.environ.get("pvporcupine_mac_API")
