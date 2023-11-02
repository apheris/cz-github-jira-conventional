from setuptools import setup

# read the contents of your README file
from os import path

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="cz_psee",
    version="1.0.0",
    py_modules=["cz_psee"],
    author="PROPHESEE",
    author_email="rvansebrouck@prophsee.ai",
    license="MIT",
    url="https://github.com/prophesee-ai/sensor_research-cz_psee",
    install_requires=["commitizen"],
    description="Extend the commitizen tools to create conventional commits and README that link to Jira and GitHub.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    entry_points={
        "commitizen.plugin": [
            "cz_psee = cz_psee:PSEECz"
        ]
    },
)
