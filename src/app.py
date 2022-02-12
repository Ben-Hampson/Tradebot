"""API. Currently not being used."""

import logging

import uvicorn
from fastapi import FastAPI

app = FastAPI()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)


@app.get("/")
async def root():
    return "Version 2.2 Online!"


@app.get("/test")
def test():
    return "Hello world."


def main():
    uvicorn.run("app:app", port=80, host="0.0.0.0", reload=True)


if __name__ == "__main__":
    main()
