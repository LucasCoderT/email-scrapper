import os

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

extra_requires = {
    "gmail": ["google-api-python-client"]
}

setuptools.setup(
    name='email_scrapper',
    version=os.getenv('VERSION', '0.6.0'),
    author="LucasCLuk",
    description="An email parser for store orders.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/LucasCLuk/email-scrapper",
    packages=setuptools.find_packages(),
    install_requires=requirements,
    extra_requires=extra_requires,
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
