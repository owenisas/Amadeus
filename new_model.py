from openai import OpenAI
import time
import base64
import mimetypes
from load_env import xAI

def image_to_data_url(image_path):
    # Determine the MIME type of the image
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        raise ValueError("Could not determine the MIME type of the image.")

    # Read the image file in binary mode
    with open(image_path, 'rb') as img_file:
        # Encode the binary data to Base64
        base64_encoded = base64.b64encode(img_file.read()).decode('utf-8')

    # Construct the data URL
    data_url = f"data:{mime_type};base64,{base64_encoded}"
    return data_url



# Example usage:
image_path = 'test.png'
data_url = image_to_data_url(image_path)
client = OpenAI(
    base_url="https://api.x.ai/v1",
    api_key=xAI,
)

time.sleep(1)
completion = client.chat.completions.create(
    model="grok-2-vision-latest",
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Describe the image"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": data_url
                }
            }
        ]
    },
        {
            "role": "assistant",
            "content": """
            The image is a screenshot of the Facebook Marketplace interface on a mobile device. Here are the key elements visible in the image:

            1. **Header**: 
               - The top part of the screen shows the Facebook Marketplace logo.
               - There are icons for notifications, messages, and user profile on the right side.
            
            2. **Navigation Tabs**: 
               - Below the header, there are tabs for "Sell", "For you", "Local", "Jobs", and "More".
            
            3. **Main Content**:
               - The main section is titled "New for you" with a message indicating that the user can see more listings like the Steamdeck (1TB).
               - Below this, there is a section titled "Today's picks".
            
            4. **Listings**:
               - **First Listing**: A Logitech G23 racing wheel, priced at $99 - $150, listed just now.
               - **Second Listing**: A 1-bed, 1-bath house in Bellevue, WA, priced at $800, listed just now.
               - **Third Listing**: A Gamin PC, priced at $600 - $1000, listed just now.
               - **Fourth Listing**: An Apple Magic Trackpad, priced at $30, listed just now.
               - **Fifth Listing**: A power adapter, listed just now.
            
            Each listing includes a small image of the item, a brief description, the price range, and the time since it was listed. The listings are displayed in a grid format.
            """
        },
        {
            "role": "user", "content": "locate the first listing using pixels using the upper left corner as the origin, tell me in x and y"
        }
    ]
)
print(completion)
print(completion.choices[0])
print(completion.choices[0].message)
print(completion.choices[0].message.content)
