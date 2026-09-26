from python.hearttwin.missing_piece.identifiability import assess_identifiability


def test_metadata_is_descriptive_only_and_never_unique_learnability():
    result = assess_identifiability(
        {
            "heart_rate_bpm": {
                "parameter_id": "heart_rate_bpm",
                "bounds": {"min": 30.0, "max": 200.0},
                "output_ids": ["cardiac_output_l_min"],
            }
        },
        {
            "cardiac_output_l_min": {
                "metric_id": "cardiac_output_l_min",
                "samples": [4.0, 4.5, 5.0],
                "unit": "L/min",
            }
        },
    )

    assert len(result) == 1
    assert result[0].status == "descriptive_only"
    assert result[0].related_output_ids == ("cardiac_output_l_min",)
    assert any("uniquely learnable" in item for item in result[0].limitations)


def test_missing_and_unsupported_metadata_are_explicit():
    unavailable = assess_identifiability(
        {"preload_index": {"parameter_id": "preload_index"}},
        None,
    )
    unsupported = assess_identifiability(
        {
            "preload_index": {
                "parameter_id": "preload_index",
                "method": "jacobian_rank",
            }
        },
        {"ejection_fraction_pct": {"metric_id": "ejection_fraction_pct"}},
    )

    assert unavailable[0].status == "unavailable"
    assert "output metadata" in unavailable[0].reason
    assert unsupported[0].status == "unsupported"
    assert "jacobian_rank" in unsupported[0].reason
