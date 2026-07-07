def test_register_device_idempotent(client, db):
    from app.models import DeviceToken

    r = client.post("/devices", json={"token": "fcm-abc", "platform": "android"})
    assert r.status_code == 201
    client.post("/devices", json={"token": "fcm-abc"})
    assert db.query(DeviceToken).count() == 1


def test_push_skips_when_unconfigured(db):
    from app import push
    from app.models import Report
    from datetime import date

    report = Report(kind="weekly", period_start=date(2026, 6, 22),
                    period_end=date(2026, 6, 28), body_md="x")
    db.add(report)
    db.commit()
    assert push.send_report_notification(db, report) == 0
