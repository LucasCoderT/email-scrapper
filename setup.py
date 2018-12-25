import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()


with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setuptools.setup(
    name='email_scrapper',
    version='0.4.1',
    author="Lucas",
    description="An email parser for store orders.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/javatechy/dokr",
    packages=setuptools.find_packages(),
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
