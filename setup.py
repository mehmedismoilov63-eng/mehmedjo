"""
GHOST Assistant Setup Script
For packaging and distribution
"""

from setuptools import setup, find_packages
import os

# Read README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="ghost-assistant",
    version="1.0.0",
    author="GHOST Team",
    author_email="contact@ghost-assistant.com",
    description="Professional Windows Voice Assistant for Uzbek and Russian languages",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/ghost-assistant",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Desktop Environment",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "black>=23.11.0",
            "flake8>=6.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ghost=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.json", "*.png", "*.wav", "*.env.example"],
    },
    data_files=[
        ("data", ["data/intents_uz.json", "data/intents_ru.json"]),
        ("config", [".env.example"]),
    ],
    keywords="voice assistant, windows, uzbek, russian, speech recognition, tts",
    project_urls={
        "Bug Reports": "https://github.com/your-username/ghost-assistant/issues",
        "Source": "https://github.com/your-username/ghost-assistant",
        "Documentation": "https://github.com/your-username/ghost-assistant/wiki",
    },
)
