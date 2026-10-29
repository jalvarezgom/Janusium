"""Pure helpers that generate human-like input patterns.

Nothing here touches a browser: each function only computes coordinates,
distances or delays, so the drivers can replay them as real input events and the
patterns stay unit-testable. Pass a seeded :class:`random.Random` as ``rng`` for
reproducible output.
"""

from __future__ import annotations

import math
import random
from typing import Optional

Point = tuple[int, int]

_SLOW_AFTER = " \t\n"
_SLOWER_AFTER = ".,;:!?"


def mouse_path(
    start: Point,
    end: Point,
    steps: Optional[int] = None,
    rng: Optional[random.Random] = None,
) -> list[Point]:
    """Return viewport points along a curved path from ``start`` to ``end``.

    The path is a cubic Bezier with randomly offset control points, traversed
    with ease-in-out spacing (slow start, fast middle, slow arrival) and a
    little jitter on intermediate points. The last point is exactly ``end``.

    Args:
        start: Starting ``(x, y)`` viewport coordinates.
        end: Target ``(x, y)`` viewport coordinates.
        steps: Number of points. Defaults to a value scaled by the distance.
        rng: Random source. Defaults to the :mod:`random` module.
    """
    rng = rng or random
    distance = math.hypot(end[0] - start[0], end[1] - start[1])
    if steps is None:
        steps = max(8, min(60, int(distance / 15)))
    if steps < 1:
        raise ValueError("steps must be at least 1")

    # Control points sit off the straight line, proportionally to the distance.
    spread = max(distance * 0.25, 5)

    def control(fraction: float) -> tuple[float, float]:
        return (
            start[0] + (end[0] - start[0]) * fraction + rng.uniform(-spread, spread),
            start[1] + (end[1] - start[1]) * fraction + rng.uniform(-spread, spread),
        )

    c1, c2 = control(0.33), control(0.66)
    points: list[Point] = []
    for index in range(1, steps + 1):
        t = index / steps
        t = t * t * (3 - 2 * t)  # smoothstep easing
        u = 1 - t
        x = u**3 * start[0] + 3 * u**2 * t * c1[0] + 3 * u * t**2 * c2[0] + t**3 * end[0]
        y = u**3 * start[1] + 3 * u**2 * t * c1[1] + 3 * u * t**2 * c2[1] + t**3 * end[1]
        if index < steps:
            x += rng.uniform(-1, 1)
            y += rng.uniform(-1, 1)
        points.append((round(x), round(y)))
    points[-1] = (int(end[0]), int(end[1]))
    return points


def typing_delays(
    text: str,
    min_delay: float = 0.05,
    max_delay: float = 0.2,
    rng: Optional[random.Random] = None,
) -> list[float]:
    """Return one delay in seconds to wait after typing each character of ``text``.

    Delays are drawn from ``[min_delay, max_delay]`` and stretched after spaces
    and punctuation. About one character in thirty is followed by a longer
    "thinking" pause, so the rhythm never settles into a constant cadence.
    """
    if min_delay < 0 or max_delay < min_delay:
        raise ValueError("Delays must satisfy 0 <= min_delay <= max_delay")
    rng = rng or random
    delays = []
    for char in text:
        delay = rng.uniform(min_delay, max_delay)
        if char in _SLOWER_AFTER:
            delay *= rng.uniform(2.0, 3.0)
        elif char in _SLOW_AFTER:
            delay *= rng.uniform(1.3, 1.8)
        if rng.random() < 0.03:
            delay += rng.uniform(max_delay, max_delay * 4)
        delays.append(delay)
    return delays


def scroll_steps(
    distance: int,
    min_step: int = 40,
    max_step: int = 160,
    rng: Optional[random.Random] = None,
) -> list[int]:
    """Split a scroll ``distance`` in pixels into wheel-sized steps.

    Steps are smaller at the start and end of the movement and larger in the
    middle. They always sum to ``distance`` and carry its sign, so negative
    distances scroll up.
    """
    if min_step < 1 or max_step < min_step:
        raise ValueError("Steps must satisfy 1 <= min_step <= max_step")
    rng = rng or random
    remaining = abs(distance)
    total = remaining
    sign = -1 if distance < 0 else 1
    steps: list[int] = []
    while remaining > 0:
        progress = 1 - remaining / total
        ease = math.sin(math.pi * progress)  # 0 at the ends, 1 in the middle
        ceiling = min_step + (max_step - min_step) * ease
        step = min(remaining, max(1, round(rng.uniform(min_step, max(min_step, ceiling)))))
        steps.append(sign * step)
        remaining -= step
    return steps
