import pytest
from app.core.security import create_access_token
from app.models.user import User, Organization
from app.models.client import TallyClient, SyncJob
from sqlalchemy import select


@pytest.mark.asyncio
async def test_client_lifecycle_duplicate_and_delete(client, test_db):
    # 1. Create a test organization and user
    org = Organization(name="Test Org")
    test_db.add(org)
    await test_db.flush()

    user = User(
        email="test_manager@example.com",
        hashed_password="hashedpassword",
        full_name="Test Manager",
        role="manager",
        org_id=org.id,
        is_active=True,
    )
    test_db.add(user)
    await test_db.flush()

    # Create access token
    token = create_access_token({"sub": user.id})
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Add client first time
    client_payload = {
        "company_name": "Unique Test Company Ltd",
        "tally_host": "localhost",
        "tally_port": 9000,
        "financial_year": "2026-2027",
    }
    response = await client.post("/api/clients", json=client_payload, headers=headers)
    assert response.status_code == 201
    created_client = response.json()
    assert created_client["company_name"] == "Unique Test Company Ltd"
    assert created_client["financial_year"] == "2026-2027"

    # 3. Add duplicate client (should fail with 400)
    response = await client.post("/api/clients", json=client_payload, headers=headers)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

    # 4. Add client with same name but different FY (should succeed)
    another_year_payload = client_payload.copy()
    another_year_payload["financial_year"] = "2025-2026"
    response = await client.post("/api/clients", json=another_year_payload, headers=headers)
    assert response.status_code == 201

    # 5. Verify different organization can create a client with same name & FY
    org2 = Organization(name="Test Org 2")
    test_db.add(org2)
    await test_db.flush()

    user2 = User(
        email="test_manager2@example.com",
        hashed_password="hashedpassword2",
        full_name="Test Manager 2",
        role="manager",
        org_id=org2.id,
        is_active=True,
    )
    test_db.add(user2)
    await test_db.flush()

    token2 = create_access_token({"sub": user2.id})
    headers2 = {"Authorization": f"Bearer {token2}"}

    response = await client.post("/api/clients", json=client_payload, headers=headers2)
    assert response.status_code == 201

    # 6. Test cascading delete
    # Let's add a sync job to the first client
    sync_job = SyncJob(client_id=created_client["id"], status="completed")
    test_db.add(sync_job)
    await test_db.flush()

    # Delete first client
    response = await client.delete(f"/api/clients/{created_client['id']}", headers=headers)
    assert response.status_code == 204

    # Verify client is deleted from db
    stmt = select(TallyClient).where(TallyClient.id == created_client["id"])
    res = await test_db.execute(stmt)
    assert res.scalar_one_or_none() is None

    # Verify sync jobs are deleted (cascade)
    stmt = select(SyncJob).where(SyncJob.client_id == created_client["id"])
    res = await test_db.execute(stmt)
    assert len(res.scalars().all()) == 0
