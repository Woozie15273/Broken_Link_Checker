import asyncio
import json
from src.manager import Manager
from src.config import BASE_DIR

async def main():
    # Load targets
    with open(BASE_DIR / "data" / "targets.json") as f:
        targets = json.load(f)

    # Execute
    director = Manager()
    await director.run(targets)

if __name__ == "__main__":
    asyncio.run(main())