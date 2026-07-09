import os
import requests
from tqdm import tqdm

def download_model(model_url="https://huggingface.co/TheBloke/dolphin-2.6-phi-2-GGUF/resolve/main/dolphin-2_6-phi-2.Q4_K_M.gguf",
                   save_path="models/dolphin-2_6-phi-2.Q4_K_M.gguf"):

    if os.path.exists(save_path):
        print(f"Model already exists at {save_path}")
        return True

    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    print(f"Downloading JARVIS Brain (Model) from {model_url}...")
    try:
        response = requests.get(model_url, stream=True)
        total_size = int(response.headers.get('content-length', 0))

        with open(save_path, 'wb') as file, tqdm(
            desc=save_path,
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for data in response.iter_content(chunk_size=1024):
                size = file.write(data)
                bar.update(size)
        print("Download complete.")
        return True
    except Exception as e:
        print(f"Download failed: {e}")
        return False
