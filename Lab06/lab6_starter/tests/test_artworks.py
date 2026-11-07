"""Lab 06: API behavior, validation, duplicates, filtering and pagination."""

import pytest


# Part 4: Happy paths

def test_list_artworks_empty(client):
    response = client.get("/artworks/")
    assert response.status_code == 200
    assert response.json() == []


def test_get_seeded_artwork(client, seeded_db):
    expected = {"id": 1, **seeded_db[0]}
    response = client.get("/artworks/1")
    assert response.status_code == 200
    assert response.json() == expected


def test_create_artwork(client, sample_artwork):
    response = client.post("/artworks/", json=sample_artwork)
    assert response.status_code == 201

    actual = response.json()
    assert isinstance(actual["id"], int)
    assert {field: value for field, value in actual.items() if field != "id"} == sample_artwork


def test_create_artwork_is_saved(client, created_artwork):
    response = client.get(f"/artworks/{created_artwork['id']}")
    assert response.status_code == 200
    assert response.json() == created_artwork


def test_update_artwork(client, created_artwork, updated_artwork):
    artwork_id = created_artwork["id"]
    expected = {"id": artwork_id, **updated_artwork}

    response = client.put(f"/artworks/{artwork_id}", json=updated_artwork)
    assert response.status_code == 200
    assert response.json() == expected

    saved_response = client.get(f"/artworks/{artwork_id}")
    assert saved_response.status_code == 200
    assert saved_response.json() == expected


def test_delete_artwork(client, created_artwork):
    artwork_id = created_artwork["id"]
    response = client.delete(f"/artworks/{artwork_id}")
    assert response.status_code == 204
    assert response.content == b""

    get_response = client.get(f"/artworks/{artwork_id}")
    assert get_response.status_code == 404
    assert get_response.json() == {"detail": "Artwork not found"}


# Part 5: Unhappy paths

@pytest.mark.parametrize(
    "method, use_body",
    [("get", False), ("put", True), ("delete", False)],
    ids=["get", "put", "delete"],
)
def test_artwork_not_found(client, sample_artwork, method, use_body):
    kwargs = {"json": sample_artwork} if use_body else {}
    response = client.request(method.upper(), "/artworks/9999", **kwargs)
    assert response.status_code == 404
    assert response.json() == {"detail": "Artwork not found"}


def test_non_integer_id(client):
    response = client.get("/artworks/mona-lisa")
    assert response.status_code == 422


def test_create_duplicate(client, created_artwork, sample_artwork):
    response = client.post("/artworks/", json=sample_artwork)
    assert response.status_code == 409
    assert response.json() == {
        "detail": "An artwork with that title and artist already exists"
    }


def test_create_duplicate_ignores_case(client, created_artwork, sample_artwork):
    duplicate = sample_artwork.copy()
    duplicate["title"] = duplicate["title"].upper()
    duplicate["artist"] = duplicate["artist"].lower()

    response = client.post("/artworks/", json=duplicate)
    assert response.status_code == 409
    assert response.json() == {
        "detail": "An artwork with that title and artist already exists"
    }


def test_update_into_duplicate(client, seeded_db):
    original_second = {"id": 2, **seeded_db[1]}
    duplicate_body = seeded_db[1].copy()
    duplicate_body["title"] = seeded_db[0]["title"]
    duplicate_body["artist"] = seeded_db[0]["artist"]

    response = client.put("/artworks/2", json=duplicate_body)
    assert response.status_code == 409

    after = client.get("/artworks/2")
    assert after.status_code == 200
    assert after.json() == original_second


def test_update_same_title_and_artist_is_allowed(client, created_artwork, sample_artwork):
    artwork_id = created_artwork["id"]
    changed = sample_artwork.copy()
    changed["museum"] = "Another Museum"

    response = client.put(f"/artworks/{artwork_id}", json=changed)
    assert response.status_code == 200
    assert response.json() == {"id": artwork_id, **changed}

    saved = client.get(f"/artworks/{artwork_id}")
    assert saved.status_code == 200
    assert saved.json() == {"id": artwork_id, **changed}


# Part 6: Parametrized validation, pagination and filtering

@pytest.mark.parametrize(
    "missing_field",
    ["title", "artist", "year", "medium", "museum", "image_url"],
)
def test_create_missing_field(client, sample_artwork, missing_field):
    body = sample_artwork.copy()
    body.pop(missing_field)
    response = client.post("/artworks/", json=body)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", missing_field]


@pytest.mark.parametrize(
    "field, bad_value",
    [("year", 3000), ("year", "nineteen-oh-seven"), ("title", "")],
    ids=["future-year", "year-not-int", "empty-title"],
)
def test_create_invalid_value(client, sample_artwork, field, bad_value):
    body = sample_artwork.copy()
    body[field] = bad_value
    response = client.post("/artworks/", json=body)
    assert response.status_code == 422


@pytest.mark.parametrize(
    "params, expected_count",
    [
        ({"skip": 0, "limit": 3}, 3),
        ({"skip": 3, "limit": 5}, 5),
        ({"limit": 0}, 0),
        ({"skip": 100, "limit": 10}, 0),
    ],
    ids=["first-three", "five-after-three", "limit-zero", "skip-past-end"],
)
def test_pagination_counts(client, seeded_db, params, expected_count):
    response = client.get("/artworks/", params=params)
    assert response.status_code == 200
    assert len(response.json()) == expected_count


@pytest.mark.parametrize(
    "params",
    [{"skip": -1}, {"limit": 500}],
    ids=["negative-skip", "limit-too-large"],
)
def test_pagination_invalid(client, params):
    response = client.get("/artworks/", params=params)
    assert response.status_code == 422


@pytest.mark.parametrize(
    "artist, expected_titles",
    [
        ("Claude Monet", ["Impression, Sunrise", "Woman with a Parasol – Madame Monet and Her Son"]),
        ("monet", ["Impression, Sunrise", "Woman with a Parasol – Madame Monet and Her Son"]),
        ("da vinci", ["Mona Lisa", "Lady with an Ermine"]),
        ("not-an-artist", []),
    ],
    ids=["exact", "lowercase-partial", "da-vinci-partial", "no-match"],
)
def test_filter_by_artist(client, seeded_db, artist, expected_titles):
    # Check exact expected titles and their ordering against the seed specification.
    response = client.get("/artworks/", params={"artist": artist})
    assert response.status_code == 200
    assert [item["title"] for item in response.json()] == expected_titles
