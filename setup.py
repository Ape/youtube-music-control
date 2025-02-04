from setuptools import setup, find_packages

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name="youtube-music-control",
    version="0.1.0",
    description="Remote control client for th-ch/youtube-music",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Lauri Niskanen",
    author_email="ape@ape3000.com",
    packages=find_packages(),
    install_requires=[
        "requests>=2.32.0",
    ],
    entry_points={
        "console_scripts": [
            "youtube-music-control=youtube_music_control.__main__:main",
        ],
    },
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Utilities",
    ],
)
