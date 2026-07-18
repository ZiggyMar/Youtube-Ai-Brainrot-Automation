git add .
git commit -m "feat: fully containerize pipeline and harden API configuration" -m "- Added Dockerfile and docker-compose.yml for global reproducibility." -m "- Updated README to replace manual setup with Docker instructions." -m "- Created .env.example template." -m "- Added startup configuration checks to prevent silent failures on missing API keys." -m "- Added explicit LLM fallback warnings."
git push
