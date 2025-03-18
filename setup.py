from setuptools import setup, find_packages

setup(
    name="ai_chat",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "sqlalchemy>=2.0.0",
        "alembic>=1.12.0",
        "pydantic>=2.4.0",
        "pydantic-settings>=2.0.0",
        "python-multipart>=0.0.6",
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.4",
        "python-dotenv>=1.0.0",
        "aiohttp>=3.9.0",
        "aiosqlite>=0.19.0",
    ],
) 