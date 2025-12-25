import os
import requests
import zipfile
import shutil

MODELS = {
    "spongebob": "https://huggingface.co/darthanonymous1/DarthRVC/resolve/main/SpongebobSquarepantsV2.zip?download=true",
    "patrick": "https://huggingface.co/Blocktoast64/Blocktoasts-RVC-Models/resolve/main/Patrick%20Star%20(Nickelodeon%20All%20Star%20Brawl%202%2C%20SpongeBob%20SquarePants).zip",
    "squidward": "https://huggingface.co/ThatBlondeGuy/Squidward-300EP/resolve/main/Squidward.zip?download=true"
}

UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(UTILS_DIR)
BASE_DIR = os.path.join(PROJECT_ROOT, "rvc_models")

def download_file(url, filename):
    print(f"Downloading {url} to {filename}...")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print("Download complete.")

def setup_model(character, url):
    target_dir = os.path.join(BASE_DIR, character)
    os.makedirs(target_dir, exist_ok=True)
    
    zip_path = os.path.join(target_dir, f"{character}.zip")
    download_file(url, zip_path)
    
    print(f"Extracting {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(target_dir)
    
    # Find .pth and .index files
    pth_file = None
    index_file = None
    
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".pth") and not pth_file:
                pth_file = os.path.join(root, file)
            elif file.endswith(".index") and not index_file:
                index_file = os.path.join(root, file)
    
    if pth_file:
        new_pth = os.path.join(target_dir, f"{character}.pth")
        if pth_file != new_pth:
            shutil.move(pth_file, new_pth)
            print(f"Renamed {pth_file} to {new_pth}")
    else:
        print(f"WARNING: No .pth file found for {character}")

    if index_file:
        new_index = os.path.join(target_dir, f"{character}.index")
        if index_file != new_index:
            shutil.move(index_file, new_index)
            print(f"Renamed {index_file} to {new_index}")
    else:
        print(f"WARNING: No .index file found for {character}")

    # Cleanup
    if os.path.exists(zip_path):
        os.remove(zip_path)
    
    # Clean up other files/folders in the target dir if needed, but for now just keeping the renamed ones is fine.
    # Actually, let's try to remove subdirectories if we moved the files out.
    for item in os.listdir(target_dir):
        item_path = os.path.join(target_dir, item)
        if os.path.isdir(item_path):
            try:
                shutil.rmtree(item_path)
            except:
                pass
        elif item not in [f"{character}.pth", f"{character}.index"]:
             # Optional: remove other files like 'added_...index' if we already renamed one, or keep them?
             # The user wants a clean structure.
             try:
                 os.remove(item_path)
             except:
                 pass

if __name__ == "__main__":
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)
        
    for char, url in MODELS.items():
        print(f"Setting up {char}...")
        try:
            setup_model(char, url)
        except Exception as e:
            print(f"Failed to setup {char}: {e}")
            
    print("Done.")
