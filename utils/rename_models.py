import os
import shutil

BASE_DIR = "rvc_models"

def rename_models():
    if not os.path.exists(BASE_DIR):
        print(f"Directory {BASE_DIR} does not exist.")
        return

    for folder_name in os.listdir(BASE_DIR):
        folder_path = os.path.join(BASE_DIR, folder_name)
        if not os.path.isdir(folder_path):
            continue

        target_name = folder_name.lower()
        
        # Files to look for
        pth_file = None
        index_file = None
        
        # Scan files
        for file in os.listdir(folder_path):
            if file.endswith(".pth"):
                pth_file = file
            elif file.endswith(".index"):
                index_file = file
        
        # Rename .pth
        if pth_file:
            old_path = os.path.join(folder_path, pth_file)
            new_name = f"{target_name}.pth"
            new_path = os.path.join(folder_path, new_name)
            
            if old_path != new_path:
                try:
                    os.rename(old_path, new_path)
                    print(f"Renamed {pth_file} -> {new_name}")
                except Exception as e:
                    print(f"Error renaming {pth_file}: {e}")
            else:
                print(f"{new_name} already correct.")
        else:
            print(f"No .pth file found in {folder_name}")

        # Rename .index
        if index_file:
            old_path = os.path.join(folder_path, index_file)
            new_name = f"{target_name}.index"
            new_path = os.path.join(folder_path, new_name)
            
            if old_path != new_path:
                try:
                    os.rename(old_path, new_path)
                    print(f"Renamed {index_file} -> {new_name}")
                except Exception as e:
                    print(f"Error renaming {index_file}: {e}")
            else:
                print(f"{new_name} already correct.")
        else:
            print(f"No .index file found in {folder_name}")

if __name__ == "__main__":
    rename_models()
