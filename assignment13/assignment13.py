import streamlit as st
import base64
from openai import OpenAI, OpenAIError, BadRequestError
from PIL import Image
import io

# Initialize client
client = OpenAI()

st.title("DALL·E 3 Image Generator")

prompt = st.text_input("Prompt", "")
negative_prompt = st.text_input("Negative Prompt (optional)", "")
aspect_ratio = st.selectbox("Aspect Ratio", ["1:1 (Square)", "16:9 (Landscape)", "4:3 (Portrait)"])

# DALL·E 3 generates 1:1 images
size = "1024x1024"

# Target output sizes for cropping
crop_map = {
    "1:1 (Square)": (1024, 1024),
    "16:9 (Landscape)": (1024, 576),  # width 1024, height adjusted for 16:9
    "4:3 (Portrait)": (1024, 768)     # width 1024, height adjusted for 4:3
}

def crop_center(img, target_size):
    target_w, target_h = target_size
    img_w, img_h = img.size
    left = (img_w - target_w) // 2
    top = (img_h - target_h) // 2
    right = left + target_w
    bottom = top + target_h
    return img.crop((left, top, right, bottom))

if st.button("Generate Image"):
    with st.spinner("Generating image with DALL·E 3..."):
        try:
            # Combine prompt and optional negative prompt
            full_prompt = prompt
            if negative_prompt.strip():
                full_prompt = f"{prompt}. Do NOT include {negative_prompt.strip()}. Make sure {negative_prompt.strip()} are not present."

            # Generate 1:1 image
            response = client.images.generate(
                model="dall-e-3",
                prompt=full_prompt,
                n=1,
                size=size,
                response_format="b64_json"
            )

            # Decode base64
            image_base64 = response.data[0].b64_json
            if image_base64:
                image_bytes = base64.b64decode(image_base64)
                img = Image.open(io.BytesIO(image_bytes))

                # Crop to target aspect ratio if needed
                if aspect_ratio != "1:1 (Square)":
                    img = crop_center(img, crop_map[aspect_ratio])

                st.image(img, caption=f"Generated Image ({aspect_ratio})", use_container_width=True)

                # Save and provide download
                img.save("generated_image.png")
                st.download_button(
                    label="Download Image",
                    data=open("generated_image.png", "rb").read(),
                    file_name="generated_image.png",
                    mime="image/png"
                )
            else:
                st.error("No image data returned. This might be a content policy block or server issue.")

        except BadRequestError as e:
            msg = str(e)
            if "content_policy" in msg.lower():
                st.error("❌ Content Policy Violation: The generated prompt was blocked.")
            else:
                st.error(f"Bad Request Error: {e}")
        except OpenAIError as e:
            st.error(f"Unexpected API Error: {e}")
        except Exception as e:
            st.error(f"Unexpected Error: {e}")
