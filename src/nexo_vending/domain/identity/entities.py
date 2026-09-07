from __future__ import annotations

from dataclasses import dataclass

from nexo_vending.domain.common.ids import UserId


@dataclass(frozen=True, slots=True)
class Operator:
    """Vending-facing operator reference.

    Full authentication / authorization lives outside this domain (Platform /
    future identity adapters). V2 only needs a stable operator identity.
    """

    id: UserId
    active: bool = True
