def test_create_inspection_returns_created_record(client) -> None:
    response = client.post(
        "/api/v1/inspections",
        json={
            "farm_id": 1,
            "shed_id": 1,
            "inspector_name": "Tester",
            "notes": "Checked ventilation and feed lines.",
            "status": "completed",
        },
    )

    data = response.json()
    assert response.status_code == 200
    assert data["inspectorName"] == "Tester"
    assert data["notes"] == "Checked ventilation and feed lines."
