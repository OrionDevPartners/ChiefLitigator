from setuptools import setup, find_packages

setup(
    name="ciphergy",
    version="1.0.0",
    description="Ciphergy — Signal extraction platform for complex adversarial domains",
    author="Analog AGI",
    author_email="info@ciphergy.ai",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "flask>=3.0.0",
        "flask-socketio>=5.3.0",
        "pydantic>=2.5.0",
        "boto3>=1.34.0",
        "httpx>=0.25.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.23.0",
            "ruff>=0.1.0",
            "mypy>=1.7.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ciphergy=ciphergy.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
