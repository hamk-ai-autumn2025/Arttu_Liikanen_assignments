import argparse
import base64
import requests
from openai import OpenAI

def main():
    parser = argparse.ArgumentParser(description="Generate images using OpenAI API.")
    parser.add_argument("--prompt", required=True, help="Prompt for image generation")
    parser.add_argument("--num_images", type=int, default=1, help="Number of images to generate (1-10)")
    parser.add_argument("--resolution", choices=["256", "512", "1024"], default="1024",
                        help="Resolution of generated image (must be 256, 512, or 1024)")
    args = parser.parse_args()

    client = OpenAI()

    # Prepare image generation parameters
    image_params = {
        "prompt": args.prompt,
        "n": args.num_images,
        "size": f"{args.resolution}x{args.resolution}",
    }

    # Generate images
    try:
        response = client.images.generate(**image_params)
    except Exception as e:
        print(f"Error generating images: {e}")
        return

    images = response.data

    # Save images locally and print download URL
    for idx, img in enumerate(images):
        base64_data = getattr(img, "b64_json", None) or (img.get("b64_json") if isinstance(img, dict) else None)
        url = getattr(img, "url", None) or (img.get("url") if isinstance(img, dict) else None)

        filename = f"generated_image_{idx + 1}.png"

        if base64_data:
            with open(filename, "wb") as f:
                f.write(base64.b64decode(base64_data))
            print(f"Image {idx + 1} saved as: {filename}")
        elif url:
            try:
                resp = requests.get(url)
                resp.raise_for_status()
                with open(filename, "wb") as f:
                    f.write(resp.content)
                print(f"Image {idx + 1} downloaded from URL and saved as: {filename}")
            except Exception as e:
                print(f"Failed to download image {idx + 1} from URL: {e}")

        if url:
            print(f"Image {idx + 1} URL: {url}")

if __name__ == "__main__":
    main()
