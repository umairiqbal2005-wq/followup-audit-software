from typing import Optional

from ldap3 import ALL, Connection, Server
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User, UserRole


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def authenticate(self, username: str, password: str) -> Optional[User]:
        if self.settings.ldap_enabled:
            user = self._authenticate_ldap(username, password)
            if user:
                return user
        return self._authenticate_local(username, password)

    def _authenticate_local(self, username: str, password: str) -> Optional[User]:
        user = self.db.query(User).filter(User.username == username, User.is_active.is_(True)).first()
        if not user or not user.hashed_password:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def _authenticate_ldap(self, username: str, password: str) -> Optional[User]:
        settings = self.settings
        server = Server(settings.ldap_url, get_info=ALL, use_ssl=settings.ldap_use_ssl)
        try:
            # Service bind to search user DN
            with Connection(
                server,
                user=settings.ldap_bind_dn,
                password=settings.ldap_bind_password,
                auto_bind=True,
            ) as conn:
                search_filter = settings.ldap_user_search_filter.format(username=username)
                conn.search(settings.ldap_base_dn, search_filter, attributes=["cn", "mail", "department"])
                if not conn.entries:
                    return None
                entry = conn.entries[0]
                user_dn = entry.entry_dn

            # Bind as user to verify password
            with Connection(server, user=user_dn, password=password, auto_bind=True):
                pass

            user = self.db.query(User).filter(User.username == username).first()
            if not user:
                email = str(entry.mail) if hasattr(entry, "mail") and entry.mail else f"{username}@example.com"
                full_name = str(entry.cn) if hasattr(entry, "cn") and entry.cn else username
                department = str(entry.department) if hasattr(entry, "department") and entry.department else None
                user = User(
                    username=username,
                    email=email,
                    full_name=full_name,
                    role=UserRole.VIEWER.value,
                    department=department,
                    ldap_dn=user_dn,
                    is_active=True,
                )
                self.db.add(user)
                self.db.commit()
                self.db.refresh(user)
            return user if user.is_active else None
        except Exception:
            return None

    def issue_token(self, user: User) -> dict:
        token = create_access_token(
            subject=user.username,
            claims={"uid": user.id, "role": user.role, "name": user.full_name},
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": self.settings.access_token_expire_minutes * 60,
        }

    def ensure_dev_admin(self) -> None:
        if self.settings.ldap_enabled:
            return
        existing = self.db.query(User).filter(User.username == self.settings.dev_admin_username).first()
        if existing:
            return
        admin = User(
            username=self.settings.dev_admin_username,
            email=self.settings.dev_admin_email,
            full_name="System Administrator",
            role=UserRole.ADMIN.value,
            hashed_password=hash_password(self.settings.dev_admin_password),
            department="IT",
            is_active=True,
        )
        self.db.add(admin)
        # Seed a few demo users for local testing
        demos = [
            ("central1", "central1@example.com", "Central Reviewer", UserRole.CENTRAL_TEAM, "Audit"),
            ("owner1", "owner1@example.com", "Process Owner", UserRole.PROCESS_OWNER, "Operations"),
            ("auditor1", "auditor1@example.com", "Lead Auditor", UserRole.AUDITOR, "Audit"),
            ("viewer1", "viewer1@example.com", "Dashboard Viewer", UserRole.VIEWER, "Management"),
        ]
        for username, email, name, role, dept in demos:
            self.db.add(
                User(
                    username=username,
                    email=email,
                    full_name=name,
                    role=role.value,
                    hashed_password=hash_password("Pass@123"),
                    department=dept,
                    is_active=True,
                )
            )
        self.db.commit()
