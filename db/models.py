from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    user_id: int
    username: Optional[str] = None
    language: str = "zh"
    language_selected: int = 0
    max_alerts: int = 100
    quiet_start: Optional[str] = None
    quiet_end: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class Monitor:
    id: int
    twitter_username: str
    last_seen_id: str = "0"
    is_active: int = 1
    created_at: Optional[str] = None


@dataclass
class UserMonitor:
    user_id: int
    monitor_id: int
    keywords: Optional[str] = None
    delivery_type: str = "telegram"
    delivery_target: Optional[str] = None


@dataclass
class MonitorJob:
    id: int
    owner_user_id: int
    delivery_type: str = "telegram"
    delivery_target: Optional[str] = None
    output_mode: str = "message"
    keywords: Optional[str] = None
    is_active: int = 1
    csv_file_path: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class AlertRecord:
    id: int
    user_id: int
    twitter_username: str
    tweet_id: str
    sent_at: Optional[str] = None
