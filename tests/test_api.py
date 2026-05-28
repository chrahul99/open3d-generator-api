from pathlib import Path
from time import sleep

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_root_endpoint():
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["docs_url"] == "/docs"
    assert response.json()["ui_url"] == "/ui"


def test_ui_is_served():
    client = TestClient(app)
    response = client.get("/ui/")

    assert response.status_code == 200
    assert "Image to 3D" in response.text


def test_storage_endpoint(tmp_path: Path):
    get_settings.cache_clear()
    settings = get_settings()
    settings.storage_dir = tmp_path
    settings.max_storage_mb = 1

    client = TestClient(app)
    response = client.get("/v1/storage")

    assert response.status_code == 200
    assert response.json()["max_bytes"] == 1024 * 1024


def test_single_image_generation(tmp_path: Path):
    get_settings.cache_clear()
    app.dependency_overrides = {}
    settings = get_settings()
    settings.storage_dir = tmp_path

    client = TestClient(app)
    response = client.post(
        "/v1/generations/image-to-3d",
        files=[("images", ("chair.png", b"fake image bytes", "image/png"))],
        data={"engine": "mock", "output_format": "obj"},
    )

    assert response.status_code == 202
    job_id = response.json()["id"]

    job = wait_for_job(client, job_id)
    assert job["status"] == "succeeded"
    assert job["mode"] == "single"

    artifact = client.get(f"/v1/generations/{job_id}/artifact")
    assert artifact.status_code == 200
    assert b"generated_asset" in artifact.content


def test_multi_image_generation(tmp_path: Path):
    get_settings.cache_clear()
    settings = get_settings()
    settings.storage_dir = tmp_path

    client = TestClient(app)
    response = client.post(
        "/v1/generations/image-to-3d",
        files=[
            ("images", ("front.png", b"front", "image/png")),
            ("images", ("side.png", b"side", "image/png")),
        ],
        data={"engine": "mock", "output_format": "obj"},
    )

    assert response.status_code == 202
    job = wait_for_job(client, response.json()["id"])
    assert job["status"] == "succeeded"
    assert job["mode"] == "multi"
    assert job["input_count"] == 2


def test_delete_generation_removes_job(tmp_path: Path):
    get_settings.cache_clear()
    settings = get_settings()
    settings.storage_dir = tmp_path

    client = TestClient(app)
    response = client.post(
        "/v1/generations/image-to-3d",
        files=[("images", ("chair.png", b"fake image bytes", "image/png"))],
        data={"engine": "mock", "output_format": "obj"},
    )
    job_id = response.json()["id"]
    assert wait_for_job(client, job_id)["status"] == "succeeded"

    delete_response = client.delete(f"/v1/generations/{job_id}")
    assert delete_response.status_code == 204
    assert client.get(f"/v1/generations/{job_id}").status_code == 404


def test_cleanup_removes_completed_jobs(tmp_path: Path):
    get_settings.cache_clear()
    settings = get_settings()
    settings.storage_dir = tmp_path

    client = TestClient(app)
    response = client.post(
        "/v1/generations/image-to-3d",
        files=[("images", ("chair.png", b"fake image bytes", "image/png"))],
        data={"engine": "mock", "output_format": "obj"},
    )
    job_id = response.json()["id"]
    assert wait_for_job(client, job_id)["status"] == "succeeded"

    cleanup_response = client.post("/v1/maintenance/cleanup?max_age_hours=0")
    assert cleanup_response.status_code == 200
    assert cleanup_response.json()["deleted"] >= 1
    assert job_id in cleanup_response.json()["job_ids"]


def test_rejects_unsupported_format():
    client = TestClient(app)
    response = client.post(
        "/v1/generations/image-to-3d",
        files=[("images", ("chair.png", b"fake image bytes", "image/png"))],
        data={"engine": "mock", "output_format": "glb"},
    )

    assert response.status_code == 400


def test_rejects_non_image_upload():
    client = TestClient(app)
    response = client.post(
        "/v1/generations/image-to-3d",
        files=[("images", ("notes.txt", b"not an image", "text/plain"))],
        data={"engine": "mock", "output_format": "obj"},
    )

    assert response.status_code == 415


def test_rejects_when_storage_limit_reached(tmp_path: Path):
    get_settings.cache_clear()
    settings = get_settings()
    settings.storage_dir = tmp_path
    settings.max_storage_mb = 0

    client = TestClient(app)
    response = client.post(
        "/v1/generations/image-to-3d",
        files=[("images", ("chair.png", b"fake image bytes", "image/png"))],
        data={"engine": "mock", "output_format": "obj"},
    )

    assert response.status_code == 507


def wait_for_job(client: TestClient, job_id: str) -> dict:
    for _ in range(50):
        response = client.get(f"/v1/generations/{job_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in {"succeeded", "failed"}:
            return payload
        sleep(0.05)
    raise AssertionError("job did not finish")
