"""Main entrypoint to run The Retirement Whisperer application server."""

import uvicorn
from whisperer.config import settings

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(" 🕵️  THE RETIREMENT WHISPERER")
    print(" Adversarial AI Resilience Platform for TIAA Retirement Systems")
    print(f" Powered by TypeSafe Jev ({settings.JEV_MODEL})")
    print("=" * 60)
    print(f"\n Dashboard running at: http://127.0.0.1:{settings.SERVER_PORT}\n")

    uvicorn.run(
        "whisperer.server.app:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=True,
    )
