from setuptools import setup, find_packages

setup(
    name="gitshuffler",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "argparse",  # built-in, but listed for clarity
    ],
    entry_points={
        "console_scripts": [
            "gitshuffler=gitshuffler.cli:main",
        ],
    },
    author="GitShuffler Team",
    description="A tool to simulate natural Git commit history",
    python_requires=">=3.10",
)
