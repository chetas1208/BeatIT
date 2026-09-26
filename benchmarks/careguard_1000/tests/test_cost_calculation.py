"""Cost calculation matches the pinned per-token prices and batch halving."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _bench_common import cost_usd

def test_cost_matches_prices():
    # 1M input + 1M output at $3/$15
    c = cost_usd("claude-sonnet-4-6",
                 {"input_tokens": 1_000_000, "output_tokens": 1_000_000})
    assert abs(c - 18.0) < 1e-6

def test_batch_is_half():
    u = {"input_tokens": 1_000_000, "output_tokens": 0}
    assert abs(cost_usd("claude-sonnet-4-6", u, batch=True)
               - cost_usd("claude-sonnet-4-6", u)/2) < 1e-9

def test_both_models_priced_identically():
    u = {"input_tokens": 500_000, "output_tokens": 200_000}
    assert cost_usd("claude-sonnet-4-5-20250929", u) == \
           cost_usd("claude-sonnet-4-6", u)

def _run():
    for k,v in list(globals().items()):
        if k.startswith("test_") and callable(v): v(); print("  ok ",k)
    print("cost-calculation tests passed")
if __name__ == "__main__": _run()
