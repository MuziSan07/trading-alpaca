"""
Unit tests for the deterministic strategy math (no real API calls).
Run with:  pytest -v
"""
from src.config import CONFIG


def test_config_loads_defaults():
    assert CONFIG.max_price == 5.00
    assert CONFIG.min_volume == 1_000_000
    assert CONFIG.cash_allocation == 0.90
    assert CONFIG.stop_pct == 0.06


def test_scale_out_sizes_sum_to_one():
    assert abs((CONFIG.tp1_size + CONFIG.tp2_size) - 1.0) < 1e-6


def test_position_sizing_math():
    cash = 1000.0
    price = 2.50
    qty = int((cash * CONFIG.cash_allocation) // price)
    assert qty == 360  # 900 / 2.50


def test_exit_levels():
    entry = 2.00
    stop = round(entry * (1 - CONFIG.stop_pct), 2)
    tp1 = round(entry * (1 + CONFIG.tp1_pct), 2)
    tp2 = round(entry * (1 + CONFIG.tp2_pct), 2)
    assert stop == 1.88   # -6%
    assert tp1 == 2.10    # +5%
    assert tp2 == 2.14    # +7%


def test_scale_out_quantities():
    qty = 100
    tp1_qty = int(qty * CONFIG.tp1_size)
    tp2_qty = qty - tp1_qty
    assert tp1_qty == 75
    assert tp2_qty == 25
