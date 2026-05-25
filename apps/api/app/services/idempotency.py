import hashlib
import time
from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class IdempotencyRecord:
    job_id: str
    expires_at: float


class InMemoryIdempotencyStore:
    def __init__(self, ttl_seconds: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._records: dict[str, IdempotencyRecord] = {}
        self._lock = Lock()

    def reserve(self, job_id: str) -> tuple[IdempotencyRecord, bool]:
        now = time.time()
        with self._lock:
            self._delete_expired(now)
            existing_record = self._records.get(job_id)
            if existing_record:
                return existing_record, False

            record = IdempotencyRecord(job_id=job_id, expires_at=now + self._ttl_seconds)
            self._records[job_id] = record
            return record, True

    def forget(self, job_id: str) -> None:
        with self._lock:
            self._records.pop(job_id, None)

    def _delete_expired(self, now: float) -> None:
        expired_keys = [key for key, record in self._records.items() if record.expires_at <= now]
        for key in expired_keys:
            del self._records[key]


def build_job_id(url: str, idempotency_key: str | None, salt: str) -> str:
    idempotency_scope = idempotency_key.strip() if idempotency_key else url
    digest = hashlib.sha256(f"{salt}:{idempotency_scope}:{url}".encode("utf-8")).hexdigest()
    return digest[:32]
