from fastapi.testclient import TestClient  # type: ignore[import-untyped]

from app.main import app


def main() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/diaries/recommendations")
        print("status:", response.status_code)
        print("response:", response.json())


if __name__ == "__main__":
    main()
