from setuptools import setup, find_packages

setup(
    name="gaspipe",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.11",
    install_requires=["pydantic>=2.10.5"],
    extras_require={
        "dev": ["pytest>=8.3.4", "pytest-cov>=6.0.0"]
    }
)
