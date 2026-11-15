"""The money check page must not invent the club's USG figures (phase 3 iteration 3, audit H1).

The backend asks when the amount received this year or the number of funded events is unknown. The page used to
start both fields at 0, so the $8,000 yearly cap showed green for a club that had already received $7,500. The
frontend has no test runner, so this test reads the page's initial state from its source.
"""

from __future__ import annotations

import re

from tests.conftest import REPO_ROOT

PAGE = REPO_ROOT / "frontend" / "src" / "pages" / "MoneyCheck.tsx"


def test_club_figures_start_empty_so_the_backend_asks() -> None:
    source = PAGE.read_text(encoding="utf-8")
    initial = re.search(r"const \[club, setClub\] = useState\(\{([^}]*)\}\)", source)
    assert initial is not None, "the club state is no longer declared as expected; update this test"
    assert re.search(r'received:\s*""', initial.group(1)) and re.search(r'funded:\s*""', initial.group(1)), initial.group(1)
