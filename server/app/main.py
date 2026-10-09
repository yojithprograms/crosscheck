from fastapi import FastAPI

app = FastAPI(title="CrossCheck API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
