import os
from huggingface_hub import hf_hub_download

def download_model(repo_id="TheBloke/dolphin-2_6-phi-2-GGUF", filename="dolphin-2_6-phi-2.Q4_K_M.gguf"):
    """
    Downloads a GGUF model from HuggingFace.
    """
    print(f"--- Downloading JARVIS Brain: {repo_id} ---")
    
    # Target directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_dir = os.path.join(base_dir, "models")
    os.makedirs(models_dir, exist_ok=True)
    
    try:
        path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=models_dir,
            local_dir_use_symlinks=False
        )
        print(f"Success! Model downloaded to: {path}")
        return path
    except Exception as e:
        print(f"Error downloading model: {e}")
        return None

if __name__ == "__main__":
    download_model()
