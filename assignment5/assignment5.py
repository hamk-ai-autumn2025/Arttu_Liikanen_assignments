import argparse
import base64
from openai import OpenAI, OpenAIError, BadRequestError

def encode_image(image_path):
    """Read an image file and return a Base64-encoded string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def main():
    parser = argparse.ArgumentParser(
        description="Analyze an image and generate a new image from its description."
    )
    parser.add_argument("image_file", help="Path to the image file to analyze")
    args = parser.parse_args()

    client = OpenAI()

    base64_image = encode_image(args.image_file)

    # Step 1: Analyze the image
    print("\n=== Step 1: Analyzing the image ===")
    try:
        vision_response = client.responses.create(
            model="gpt-4.1",
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Describe this image in detail."},
                    {"type": "input_image", "image_url": f"data:image/jpeg;base64,{base64_image}"}
                ]
            }]
        )
        description = vision_response.output_text
        print("\nDescription of the input image:\n")
        print(f"\"{description}\"\n")
    except BadRequestError as e:
        msg = str(e)
        if "content_policy" in msg.lower():
            print("\n" + "="*60)
            print("CONTENT POLICY VIOLATION")
            print("The input image was flagged by OpenAI's safety system.")
            print("="*60 + "\n")
        else:
            print(f"BAD REQUEST ERROR: {e}")
        return
    except OpenAIError as e:
        print(f"UNEXPECTED ERROR analyzing image: {e}")
        return

    # Step 2: Generate a new image using DALL·E 3 from the description
    print("=== Step 2: Generating a new image with DALL·E 3 ===")
    try:
        generation_response = client.images.generate(
            model="dall-e-3",
            prompt=description,
            n=1,
            size="1024x1024",
            response_format="b64_json"
        )

        image_base64 = generation_response.data[0].b64_json
        if image_base64:
            output_file = "generated_image.png"
            with open(output_file, "wb") as f:
                f.write(base64.b64decode(image_base64))
            print(f"\nGenerated image saved as: {output_file}\n")
        else:
            print("\n" + "="*60)
            print("ERROR: No image was returned by the API.")
            print("This could be due to a content policy violation or another issue.")
            print("="*60 + "\n")

    except BadRequestError as e:
        msg = str(e)
        if "content_policy" in msg.lower():
            print("\n" + "="*60)
            print("CONTENT POLICY VIOLATION")
            print("The generated image prompt was rejected by OpenAI's safety system.")
            print("="*60 + "\n")
        else:
            print(f"BAD REQUEST ERROR: {e}")
    except OpenAIError as e:
        print(f"UNEXPECTED ERROR generating image: {e}")

if __name__ == "__main__":
    main()