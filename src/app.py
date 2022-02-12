import logging

import uvicorn
from fastapi import FastAPI

app = FastAPI()

loglevel = 10
logging.basicConfig()
logging.getLogger().setLevel(loglevel)
logging.info("Reporting INFO-level messages")


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
