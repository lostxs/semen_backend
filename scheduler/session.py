from db.session import async_session


def async_session_factory():
    """Factory function to generate new SQLAlchemy AsyncSession instances."""
    return async_session()
