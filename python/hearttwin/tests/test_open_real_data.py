from pathlib import Path

import numpy as np
import pytest

from python.hearttwin.open_real_data import load_ptb_record, load_uci_rows, normalize_uci_case


def test_load_ptb_record_reads_12_lead_format_16(tmp_path: Path) -> None:
    values = np.arange(36, dtype="<i2").reshape(3, 12)
    (tmp_path / "sample.dat").write_bytes(values.tobytes())
    lead_lines = [
        f"sample.dat 16 1000.0(0)/mV 16 0 0 0 0 {lead}"
        for lead in ("I", "II", "III", "AVR", "AVL", "AVF", "V1", "V2", "V3", "V4", "V5", "V6")
    ]
    (tmp_path / "sample.hea").write_text("sample 12 100 3\n" + "\n".join(lead_lines) + "\n")

    record = load_ptb_record(tmp_path / "sample.hea")

    assert record["signals_mv"].shape == (3, 12)
    assert record["sampling_frequency_hz"] == 100
    assert record["signals_mv"][2, 11] == pytest.approx(0.035)


def test_load_ptb_record_rejects_wrong_sample_count(tmp_path: Path) -> None:
    (tmp_path / "sample.dat").write_bytes(np.arange(12, dtype="<i2").tobytes())
    lines = ["sample 12 100 3"] + [
        f"sample.dat 16 1000.0(0)/mV 16 0 0 0 0 {lead}"
        for lead in ("I", "II", "III", "AVR", "AVL", "AVF", "V1", "V2", "V3", "V4", "V5", "V6")
    ]
    (tmp_path / "sample.hea").write_text("\n".join(lines) + "\n")

    with pytest.raises(ValueError, match="expected 36 samples"):
        load_ptb_record(tmp_path / "sample.hea")


@pytest.mark.parametrize("frequency", ["0", "-1", "nan"])
def test_load_ptb_record_rejects_invalid_frequency(tmp_path: Path, frequency: str) -> None:
    (tmp_path / "sample.dat").write_bytes(np.arange(12, dtype="<i2").tobytes())
    lines = [f"sample 12 {frequency} 1"] + [
        f"sample.dat 16 1000.0(0)/mV 16 0 0 0 0 {lead}"
        for lead in ("I", "II", "III", "AVR", "AVL", "AVF", "V1", "V2", "V3", "V4", "V5", "V6")
    ]
    (tmp_path / "sample.hea").write_text("\n".join(lines) + "\n")

    with pytest.raises(ValueError, match="sampling frequency"):
        load_ptb_record(tmp_path / "sample.hea")


def test_uci_loader_and_normalizer_preserve_missing_modalities(tmp_path: Path) -> None:
    header = (
        "age,anaemia,creatinine_phosphokinase,diabetes,ejection_fraction,"
        "high_blood_pressure,platelets,serum_creatinine,serum_sodium,sex,"
        "smoking,time,death_event\n"
    )
    rows = [
        f"{75 + index / 1000},0,582,0,20,1,265000,1.9,130,1,0,4,1\n"
        for index in range(299)
    ]
    path = tmp_path / "data.csv"
    path.write_text(header + "".join(rows))

    rows = load_uci_rows(path)
    case = normalize_uci_case(rows[0], 1)

    assert case["observed"]["ejection_fraction_pct"] == 20
    assert case["priors"] == {}
    assert "raw_ecg" in case["missing"]
    assert "raw_echo" in case["missing"]
    assert case["integrity"]["cross_dataset_stitching"] is False


def test_uci_loader_rejects_duplicate_and_surplus_rows(tmp_path: Path) -> None:
    header = ",".join(UCI_COLUMNS := (
        "age", "anaemia", "creatinine_phosphokinase", "diabetes", "ejection_fraction",
        "high_blood_pressure", "platelets", "serum_creatinine", "serum_sodium", "sex",
        "smoking", "time", "death_event",
    ))
    rows = [
        f"{75 + index / 1000},0,582,0,20,1,265000,1.9,130,1,0,4,1"
        for index in range(299)
    ]
    duplicate_path = tmp_path / "duplicate.csv"
    duplicate_path.write_text(header + "\n" + "\n".join([rows[0], rows[0], *rows[2:]]) + "\n")
    with pytest.raises(ValueError, match="duplicate rows"):
        load_uci_rows(duplicate_path)

    surplus_path = tmp_path / "surplus.csv"
    surplus_path.write_text(header + "\n" + "\n".join([rows[0] + ",extra", *rows[1:]]) + "\n")
    with pytest.raises(ValueError, match="surplus CSV values"):
        load_uci_rows(surplus_path)


@pytest.mark.parametrize("gain", ["0", "nan"])
def test_load_ptb_record_rejects_invalid_gain(tmp_path: Path, gain: str) -> None:
    (tmp_path / "sample.dat").write_bytes(np.arange(12, dtype="<i2").tobytes())
    lines = ["sample 12 100 1"] + [
        f"sample.dat 16 {gain}(0)/mV 16 0 0 0 0 {lead}"
        for lead in ("I", "II", "III", "AVR", "AVL", "AVF", "V1", "V2", "V3", "V4", "V5", "V6")
    ]
    (tmp_path / "sample.hea").write_text("\n".join(lines) + "\n")

    with pytest.raises(ValueError, match="gains"):
        load_ptb_record(tmp_path / "sample.hea")


@pytest.mark.parametrize(
    ("field", "bad_value", "message"),
    [
        ("ejection_fraction", "200", "ejection fraction"),
        ("platelets", "NaN", "invalid numeric"),
        ("diabetes", "2", "invalid binary"),
        ("time", "-1", "invalid numeric"),
    ],
)
def test_uci_loader_rejects_invalid_domains(
    tmp_path: Path, field: str, bad_value: str, message: str
) -> None:
    fields = [
        "age", "anaemia", "creatinine_phosphokinase", "diabetes", "ejection_fraction",
        "high_blood_pressure", "platelets", "serum_creatinine", "serum_sodium", "sex",
        "smoking", "time", "death_event",
    ]
    values = ["75", "0", "582", "0", "20", "1", "265000", "1.9", "130", "1", "0", "4", "1"]
    values[fields.index(field)] = bad_value
    path = tmp_path / "data.csv"
    # Preserve the source row-count contract while varying only the first row.
    valid_rows = [
        f"{75 + index / 1000},0,582,0,20,1,265000,1.9,130,1,0,4,1"
        for index in range(1, 299)
    ]
    path.write_text(
        ",".join(fields) + "\n" + ",".join(values) + "\n" + "\n".join(valid_rows) + "\n"
    )

    with pytest.raises(ValueError, match=message):
        load_uci_rows(path)
