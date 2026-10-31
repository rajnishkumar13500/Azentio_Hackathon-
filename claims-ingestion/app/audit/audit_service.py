import json
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.persistence.models.import_models import ImportAuditEvent

class AuditService:
    @staticmethod
    def log_event(
        db: Session,
        import_id: str,
        event_type: str,
        actor: str = "system",
        event_details: Optional[Dict[str, Any]] = None
    ) -> ImportAuditEvent:
        event = ImportAuditEvent(
            import_id=import_id,
            event_type=event_type,
            actor=actor,
            event_details=json.dumps(event_details, default=str) if event_details else None,
            created_at=datetime.utcnow()
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def get_events_for_import(db: Session, import_id: str):
        return db.query(ImportAuditEvent).filter(
            ImportAuditEvent.import_id == import_id
        ).order_by(ImportAuditEvent.created_at.asc()).all()
