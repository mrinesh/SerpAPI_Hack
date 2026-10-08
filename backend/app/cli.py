"""Developer command line. Every search goes through the gateway, so modes and budgets apply.

    uv run python -m app.cli serp google q="flat for sale in Whitefield Bangalore"
    uv run python -m app.cli serp google_maps q="flats for sale Whitefield"
    uv run python -m app.cli serp google q="..." start=10
    uv run python -m app.cli serp google_maps_directions start_coords=12.97,77.75 \
        end_addr="Manyata Tech Park, Bengaluru" time=depart_at:1791882000
    uv run python -m app.cli budget
    uv run python -m app.cli llm "Reply with one word: ready"
    uv run python -m app.cli llm --tier lite "..."

Engine defaults (location, gl, hl, google_domain) come from integrations/serpapi/engines.py;
extra key=value pairs override them. Set SERPAPI_MODE=record to save responses as fixtures.

`llm` sends one prompt straight to the DeepSeek provider, live, whatever LLM_MODE says: it is a
connectivity and prompt check, not a pipeline call, so nothing is cached or recorded.
"""

import argparse
import sys
from typing import Any

from app.config import get_settings
from app.core.errors import AppError
from app.db.session import SessionLocal, init_db
from app.integrations.llm.base import ModelTier
from app.integrations.llm.deepseek import DeepSeekProvider
from app.integrations.serpapi import engines
from app.integrations.serpapi.gateway import SerpApiGateway
from app.schemas.common import GeoPoint, SerpEngine
from app.services.budget import get_budget_status

BUILDERS = {
    SerpEngine.GOOGLE: engines.google_search,
    SerpEngine.GOOGLE_LOCAL: engines.google_local,
    SerpEngine.GOOGLE_MAPS: engines.google_maps_search,
    SerpEngine.GOOGLE_NEWS: engines.google_news,
    SerpEngine.GOOGLE_MAPS_DIRECTIONS: engines.google_maps_directions,
}
RESULT_BLOCKS = ("organic_results", "local_results", "news_results")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    serp = commands.add_parser("serp", help="run one SerpApi search through the gateway")
    serp.add_argument("engine", choices=[str(e) for e in BUILDERS])
    serp.add_argument(
        "params",
        nargs="+",
        help='key=value pairs; q="..." is required (directions: start_coords, end_addr)',
    )
    serp.add_argument("--show", type=int, default=10, help="results to print per block")
    commands.add_parser("budget", help="searches used this month and left on the account")
    llm = commands.add_parser("llm", help="send one prompt to the LLM provider (live)")
    llm.add_argument("prompt")
    llm.add_argument("--tier", choices=[str(t) for t in ModelTier], default=ModelTier.REASONING)
    args = parser.parse_args(argv)

    settings = get_settings()
    if args.command == "llm":
        return _llm(DeepSeekProvider(settings), args.prompt, ModelTier(args.tier))

    init_db()
    with SessionLocal() as db:
        try:
            if args.command == "budget":
                print(get_budget_status(db, settings).model_dump_json(indent=2))
                return 0
            overrides = _parse_pairs(args.params)
            engine = SerpEngine(args.engine)
            params = _params(parser, engine, overrides, settings)
            result = SerpApiGateway(settings, db).search(engine, params)
        except AppError as exc:
            print(f"error [{exc.code}]: {exc.message}", file=sys.stderr)
            return 1

    print(f"mode={settings.serpapi_mode} live={result.live} search_id={result.search_id}")
    print(f"params={result.params}")
    _print_directions(result.data)
    for block in RESULT_BLOCKS:
        items = _items(result.data.get(block))
        if items:
            print(f"\n{block}: {len(items)}")
            for item in items[: args.show]:
                print(f"  #{item.get('position')} {item.get('title')}")
                print(f"     {item.get('link') or item.get('address') or ''}")
    return 0


def _params(parser, engine: SerpEngine, overrides: dict[str, Any], settings) -> dict[str, Any]:
    if engine is SerpEngine.GOOGLE_MAPS_DIRECTIONS:
        if not overrides.get("start_coords") or not overrides.get("end_addr"):
            parser.error("start_coords=lat,lng and end_addr=... are required")
        lat, _, lng = str(overrides["start_coords"]).partition(",")
        _, params = engines.google_maps_directions(
            GeoPoint(lat=float(lat), lng=float(lng)),
            str(overrides["end_addr"]),
            settings,
            depart_at=settings.commute_depart_at,
        )
    else:
        q = overrides.pop("q", None)
        if not q:
            parser.error('q="..." is required')
        _, params = BUILDERS[engine](q, settings)
    params.update(overrides)
    return params


def _print_directions(data: dict[str, Any]) -> None:
    for place in data.get("places_info") or []:
        print(f"place: {place.get('address')} {place.get('gps_coordinates')}")
    for route in data.get("directions") or []:
        print(
            f"route via {route.get('via')}: {route.get('formatted_duration')} "
            f"({route.get('duration')} s), {route.get('formatted_distance')}, "
            f"typical {route.get('typical_duration_range')}, {route.get('extensions')}"
        )


def _llm(provider: DeepSeekProvider, prompt: str, tier: ModelTier) -> int:
    print(f"provider={provider.name} model={provider.model_for(tier)} tier={tier}")
    try:
        print(provider.generate_text(task="cli", prompt=prompt, tier=tier))
    except AppError as exc:
        print(f"error [{exc.code}]: {exc.message}", file=sys.stderr)
        return 1
    return 0


def _parse_pairs(pairs: list[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            raise SystemExit(f"expected key=value, got {pair!r}")
        parsed[key] = int(value) if value.isdigit() else value
    return parsed


def _items(block: Any) -> list[dict[str, Any]]:
    # Google Search nests local results under "places"; the Local and Maps engines don't.
    if isinstance(block, dict):
        block = block.get("places", [])
    return block if isinstance(block, list) else []


if __name__ == "__main__":
    sys.exit(main())
