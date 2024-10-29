from setuptools import setup, find_packages

setup(
    name="prbot",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "PyGithub",
        "gitpython",
        "Click",
        "python-dotenv",
        "openai",
    ],
    entry_points={
        "console_scripts": [
            "prbot=prbot.main:cli",
        ],
    },
)
