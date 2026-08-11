from typing import Optional

from ldap3 import ALL, Connection, Server
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models import AuditSegment, Region, User, UserRole
from app.services.access import ALL_REGIONS, ALL_SEGMENTS, set_user_regions, set_user_segments


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
        user = (
            self.db.query(User)
            .options(joinedload(User.region_access), joinedload(User.segment_access))
            .filter(User.username == username, User.is_active.is_(True))
            .first()
        )
        if not user or not user.hashed_password:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def _authenticate_ldap(self, username: str, password: str) -> Optional[User]:
        settings = self.settings
        server = Server(settings.ldap_url, get_info=ALL, use_ssl=settings.ldap_use_ssl)
        try:
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

            with Connection(server, user=user_dn, password=password, auto_bind=True):
                pass

            user = (
                self.db.query(User)
                .options(joinedload(User.region_access), joinedload(User.segment_access))
                .filter(User.username == username)
                .first()
            )
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
            claims={
                "uid": user.id,
                "role": user.role,
                "name": user.full_name,
                "regions": sorted({r.region for r in user.region_access or []}),
                "segments": sorted({s.segment for s in user.segment_access or []}),
            },
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": self.settings.access_token_expire_minutes * 60,
        }

    def _upsert_local_user(
        self,
        *,
        username: str,
        email: str,
        full_name: str,
        role: UserRole,
        password: str,
        department: str | None,
        regions: list[str],
        segments: list[str],
        reset_password: bool = True,
    ) -> User:
        user = self.db.query(User).filter(User.username == username).first()
        if not user:
            user = User(
                username=username,
                email=email,
                full_name=full_name,
                role=role.value,
                department=department,
                hashed_password=hash_password(password),
                is_active=True,
            )
            self.db.add(user)
            self.db.flush()
        else:
            user.email = email
            user.full_name = full_name
            user.role = role.value
            user.department = department
            user.is_active = True
            if reset_password:
                user.hashed_password = hash_password(password)
        set_user_regions(self.db, user, regions)
        set_user_segments(self.db, user, segments)
        return user

    def ensure_dev_admin(self) -> None:
        """
        Idempotent local bootstrap:
        - always ensure `admin` and `umair` exist as ADMIN with known passwords
        - seed demo regional users if missing
        - grant every ADMIN full region/segment lists for UI clarity
        """
        if not self.settings.should_bootstrap_dev_users:
            return

        # Primary break-glass admin
        self._upsert_local_user(
            username=self.settings.dev_admin_username,
            email=self.settings.dev_admin_email,
            full_name="System Administrator",
            role=UserRole.ADMIN,
            password=self.settings.dev_admin_password,
            department="IT",
            regions=ALL_REGIONS,
            segments=ALL_SEGMENTS,
            reset_password=True,
        )

        # Project owner admin (Umair)
        self._upsert_local_user(
            username="umair",
            email="umair.iqbal2005@gmail.com",
            full_name="Umair Iqbal",
            role=UserRole.ADMIN,
            password=self.settings.dev_admin_password,
            department="IT",
            regions=ALL_REGIONS,
            segments=ALL_SEGMENTS,
            reset_password=True,
        )

        demos = [
            ("central1", "central1@example.com", "Central Reviewer", UserRole.CENTRAL_TEAM, "Audit", ALL_REGIONS, ALL_SEGMENTS),
            ("owner1", "owner1@example.com", "Process Owner", UserRole.PROCESS_OWNER, "Operations", [Region.CENTRAL.value], ALL_SEGMENTS),
            ("auditor1", "auditor1@example.com", "Lead Auditor", UserRole.AUDITOR, "Audit", ALL_REGIONS, ALL_SEGMENTS),
            ("viewer1", "viewer1@example.com", "Dashboard Viewer", UserRole.VIEWER, "Management", [Region.CENTRAL.value], [AuditSegment.MANAGEMENT.value]),
            ("khurrum", "khurrum@example.com", "Khurrum North", UserRole.VIEWER, "North Region", [Region.NORTH.value], ALL_SEGMENTS),
            ("north_auditor", "north.auditor@example.com", "North Auditor", UserRole.AUDITOR, "North Region", [Region.NORTH.value], ALL_SEGMENTS),
            ("south_viewer", "south.viewer@example.com", "South Viewer", UserRole.VIEWER, "South Region", [Region.SOUTH.value], ALL_SEGMENTS),
        ]
        for username, email, name, role, dept, regions, segments in demos:
            self._upsert_local_user(
                username=username,
                email=email,
                full_name=name,
                role=role,
                password=self.settings.dev_admin_password,
                department=dept,
                regions=regions,
                segments=segments,
                reset_password=True,
            )

        # Any ADMIN should have full catalog checked for the Users UI
        admins = self.db.query(User).filter(User.role == UserRole.ADMIN.value).all()
        for admin in admins:
            set_user_regions(self.db, admin, ALL_REGIONS)
            set_user_segments(self.db, admin, ALL_SEGMENTS)

        self.db.commit()
