"""
Register job-board scrapers on a ScraperManager from YAML config.

Used by the CLI and the Job Radar GUI so registration stays in one place.
"""

from __future__ import annotations

import logging
from typing import AbstractSet, Callable, FrozenSet, Optional, Tuple

from .builtin_scraper import BuiltInScraper
from .dice_scraper import DiceScraper
from .glassdoor_scraper import GlassdoorScraper
from .greenhouse_scraper import GreenhouseScraper
from .indeed_scraper import IndeedScraper
from .lever_scraper import LeverScraper
from .linkedin_scraper import LinkedInScraper
from .remoteok_scraper import RemoteOkScraper
from .remotive_scraper import RemotiveScraper
from .scraper_manager import ScraperManager
from .upwork_scraper import UpworkScraper
from .wellfound_scraper import WellfoundScraper
from .weworkremotely_scraper import WeWorkRemotelyScraper

log = logging.getLogger(__name__)

# Sources that must not run automated scrapes from the GUI (plan requirement).
MANUAL_SOURCE_KEYS: FrozenSet[str] = frozenset(
    {"linkedin", "glassdoor", "upwork"},
)

SOURCE_REGISTER_ORDER: Tuple[str, ...] = (
    "indeed",
    "linkedin",
    "glassdoor",
    "remotive",
    "weworkremotely",
    "remoteok",
    "wellfound",
    "builtin",
    "dice",
    "greenhouse",
    "lever",
    "upwork",
)


def source_key_allowed(
    key: str,
    yaml_config: dict,
    *,
    enabled_sources: Optional[AbstractSet[str]] = None,
    db_enabled_sources: Optional[AbstractSet[str]] = None,
    skip_manual: bool = True,
) -> bool:
    """Whether a source key would be registered (without side effects)."""
    boards = yaml_config.get("job_boards", {})
    if not boards.get(key, {}).get("enabled", True):
        return False
    if enabled_sources is not None and key not in enabled_sources:
        return False
    if db_enabled_sources is not None and key not in db_enabled_sources:
        return False
    if skip_manual and key in MANUAL_SOURCE_KEYS:
        return False
    return True


def register_default_scrapers(
    manager: ScraperManager,
    yaml_config: dict,
    *,
    enabled_sources: Optional[AbstractSet[str]] = None,
    db_enabled_sources: Optional[AbstractSet[str]] = None,
    skip_manual: bool = True,
    echo_registered: Optional[Callable[[str], None]] = None,
) -> None:
    """
    Register scrapers according to ``job_boards`` in yaml_config.

    If ``enabled_sources`` is set, only those board keys are registered
    (still subject to YAML ``enabled``).

    If ``db_enabled_sources`` is set (Job Radar), the key must also appear
    in that set for registration.

    If ``skip_manual`` is True, linkedin / glassdoor / upwork are never
    registered (browser/manual sources).

    ``echo_registered`` is an optional callback(name: str) for CLI messages.
    """
    boards = yaml_config.get("job_boards", {})

    def allow(key: str) -> bool:
        return source_key_allowed(
            key,
            yaml_config,
            enabled_sources=enabled_sources,
            db_enabled_sources=db_enabled_sources,
            skip_manual=skip_manual,
        )

    def echo(msg: str) -> None:
        if echo_registered:
            echo_registered(msg)

    if allow("indeed"):
        manager.register_scraper(IndeedScraper())
        echo("📋 Registered: Indeed")

    if allow("linkedin"):
        manager.register_scraper(LinkedInScraper())
        echo("📋 Registered: LinkedIn Jobs")

    if allow("glassdoor"):
        manager.register_scraper(GlassdoorScraper())
        echo("📋 Registered: Glassdoor")

    if allow("remotive"):
        manager.register_scraper(RemotiveScraper())
        echo("📋 Registered: Remotive")

    if allow("weworkremotely"):
        manager.register_scraper(WeWorkRemotelyScraper())
        echo("📋 Registered: We Work Remotely")

    if allow("remoteok"):
        manager.register_scraper(RemoteOkScraper())
        echo("📋 Registered: Remote OK")

    if allow("wellfound"):
        manager.register_scraper(WellfoundScraper())
        echo("📋 Registered: Wellfound")

    if allow("builtin"):
        manager.register_scraper(BuiltInScraper())
        echo("📋 Registered: Built In")

    if allow("dice"):
        manager.register_scraper(DiceScraper())
        echo("📋 Registered: Dice")

    if allow("greenhouse"):
        manager.register_scraper(GreenhouseScraper())
        echo("📋 Registered: Greenhouse boards")

    if allow("lever"):
        manager.register_scraper(LeverScraper(boards.get("lever", {})))
        echo("📋 Registered: Lever job sites")

    if allow("upwork"):
        manager.register_scraper(UpworkScraper())
        echo("📋 Registered: Upwork")
