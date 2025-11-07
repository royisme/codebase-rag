"""Version information for Code Graph Knowledge System."""

__version__ = "0.7.0"
__version_info__ = tuple(int(i) for i in __version__.split("."))

# Feature flags based on version
FEATURES = {
    "code_graph": True,           # Available since 0.1.0
    "memory_store": True,          # Available since 0.6.0
    "auto_extraction": True,       # Available since 0.7.0
    "knowledge_rag": True,         # Available since 0.2.0
}

# Deployment modes
DEPLOYMENT_MODES = ["minimal", "standard", "full"]


def get_version() -> str:
    """Get the current version string."""
    return __version__


def get_version_info() -> tuple:
    """Get the version as a tuple of integers."""
    return __version_info__


def get_features() -> dict:
    """Get available features for this version."""
    return FEATURES.copy()
