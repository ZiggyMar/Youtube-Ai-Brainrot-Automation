import re

def patch_readme():
    path = "README.md"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # We want to replace everything between "## 🛠️ Installation & Setup" and the next "---"
    pattern = re.compile(r"(## 🛠️ Installation & Setup\n\n)(.*?)(?=\n---\n)", re.DOTALL)
    
    new_setup = """### 1. Prerequisites
Ensure you have the following installed on your system:
*   [Docker](https://www.docker.com/products/docker-desktop)
*   [Docker Compose](https://docs.docker.com/compose/install/)
*   Git

### 2. Clone the Repository
```bash
git clone https://github.com/ZiggyMar/Youtube-Ai-Brainrot-Automation.git
cd Youtube-Ai-Brainrot-Automation
```

### 3. Configure Environment Variables
Copy the template to create your `.env` file (do not commit this file). Add your API keys:
```bash
cp .env.example .env
```
*(Note: The project uses a fallback system, so you only strictly need one valid key to start!)*

### 4. Build and Run via Docker
The entire environment (including FFmpeg and all Python dependencies) is containerized for zero-setup execution. Simply run:
```bash
docker-compose up --build
```
Your generated videos will appear automatically in your local `output/` folder!"""

    new_content = pattern.sub(r"\1" + new_setup, content)
    
    # Also update step 2 of workflow guide just in case it mentions python core/main.py
    new_content = new_content.replace(
        "Execute the main script to start generating videos:\n```bash\npython core/main.py\n```",
        "Execute the pipeline to start generating videos:\n```bash\ndocker-compose up\n```"
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
        
if __name__ == "__main__":
    patch_readme()
    print("README updated for Docker instructions.")
