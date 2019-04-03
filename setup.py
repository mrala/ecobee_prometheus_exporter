from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="ecobee_exporter",
    version="0.1.0",
    author="Ali Yahya",
    author_email="amyahya@gmail.com",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    description="Export Ecobee metrics for Prometheus",
    dependency_links=[
        "git+ssh://git@github.com/mumblepins/Pyecobee.git#egg=Pyecobee"
    ],
    install_requires=[
        "prometheus_client",
        "Pyecobee"
    ],
    license="MIT",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    url="https://github.com/mrala/ecobee_prometheus_exporter",
    entry_points={
        "console_scripts": [
            "ecobee_exporter = ecobee_exporter:exporter_main",
        ],
    },
)
