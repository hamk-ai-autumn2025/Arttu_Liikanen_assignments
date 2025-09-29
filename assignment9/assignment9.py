import argparse
import base64
from openai import OpenAI, OpenAIError

def encode_image(image_path):
    """Read an image file and return a Base64-encoded string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def main():
    parser = argparse.ArgumentParser(
        description="Analyze multiple images and generate a marketing description and slogans based on them."
    )
    parser.add_argument("image_files", nargs='+', help="Paths to the image files to analyze")
    args = parser.parse_args()

    # Ask the user for a description of the images
    user_description = input("Please enter a description of the images: ")

    client = OpenAI()

    # Encode all images
    base64_images = [encode_image(image_path) for image_path in args.image_files]

    # Prepare input content for all images
    input_content = [
        {"type": "input_text", "text": f"Here is a user-provided description of the images: '{user_description}'. Write a marketing description for these images as well as 3 different slogans. No preamble. If the user description is completely different from the images, prioritize the image content."}
    ]
    for base64_image in base64_images:
        input_content.append({"type": "input_image", "image_url": f"data:image/jpeg;base64,{base64_image}"})

    # Step 1: Analyze the images
    print("\n=== Analyzing the images ===")
    try:
        vision_response = client.responses.create(
            model="gpt-4.1-nano",
            input=[{
                "role": "user",
                "content": input_content
            }]
        )
        description = vision_response.output_text
        print("\nDescription of the input images:\n")
        print(f"\"{description}\"\n")
    except OpenAIError as e:
        print(f"UNEXPECTED ERROR analyzing images: {e}")
        return

if __name__ == "__main__":
    main()