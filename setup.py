from setuptools import find_packages, setup

setup(
    name="overhead_annotator",
    version="0.0.1",
    url="",
    author="",
    author_email="",
    description="Framework for annotating overhead images",
    package_dir={"": "src"},
    packages=find_packages("src"),
    package_data={"": ["*.yaml"]},
    install_requires=['contextily', 'pyproj'],
)
