import logging

import uvicorn
from appliction import create_app
from config import setings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn_main")

app = create_app()
logger.info("app created")

if __name__ == "__main__":
    logger.info("server running")
    uvicorn.run(
        "main:app",
        host=setings.server_adress.split(":")[0],
        port=int(setings.server_adress.split(":")[1]),
        reload=True,
    )
