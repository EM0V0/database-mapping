"""
Build a realistic multi-sheet hospital-style XLSX demo for the mapping UI.

Row 1: technical column headers compatible with Flask identifier regex.
Row 2: English column hints surfaced as UI comments.
Row 3+: synthetic administrative rows (fabricated identifiers only).

Writes to ``fixtures/`` and copies into ``public/fixtures/`` for dev-server GET.

Usage::

    cd database-mapping
    python fixtures/build_hospital_ehr_demo_xlsx.py
"""

from __future__ import annotations

import random
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
_OUT_FIXTURE = _HERE / "demo_hospital_ehr_messy_multi_sheet.xlsx"
_PUBLIC_DIR = _REPO / "public" / "fixtures"

RNG = random.Random(20260205)

HEADERS_MZJZ = [
    "BRJZLSH",
    "MZBLH",
    "MRN_STABLE",
    "HZXMLY",
    "XBGB",
    "CSRQ8",
    "SFZ_MASK4",
    "SJHM",
    "JTZZ",
    "XZQHDM6",
    "LXRXM",
    "LXRDH",
    "XXABO",
    "RHD",
    "GMYTS",
    "JZLB",
    "JGDM",
    "KSDM",
    "MZZLKSSJ",
    "RYRQSJZY",
    "CYJSSJZY",
    "JJCDFJ",
    "ZSJY",
    "XBSJY",
    "YZYZGZH",
    "YZYXM",
    "HZKSMCFJ",
    "CBZDBM_ICD10",
    "QTZDBM_PIPE",
    "SSZ_CM3_MAIN",
    "SSF_CM3_ADD",
    "DRGJFZ_DRAFT",
    "SFDBFY",
    "RYTJDM",
    "CYQWDM",
    "ZYSSC_XS",
    "ZFYFEN",
    "YLFF_PRIMARY",
    "YLFF_EC",
    "GRZFLXJN",
    "SG_CM",
    "TZ_KG",
    "SYMMHG_LAST",
    "SZYMMHG_LAST",
    "XIN_LV_BPM",
    "HXPLC_M",
    "SPO2_PCT_RA",
    "TWSSD_LAST",
]

COMMENTS_MZJZ = [
    "Facility visit episode surrogate key bridging feeds",
    "Outpatient chart number scoped to campus alias",
    "Enterprise MPI patient identifier stable across venues",
    "Legal name snapshot captured at registration",
    "Administrative sex code 1 male 2 female 9 unknown",
    "Birth date stored as YYYYMMDD integer",
    "Masked national/resident identifier tail retained for auditing",
    "Patient primary mobile handset number",
    "Free-text mailing or domicile line",
    "Statistical locality code truncated to leading six digits",
    "Emergency contact full name captured at intake",
    "Emergency contact dial string before normalization job",
    "ABO phenotype recorded during admission intake vitals block",
    "Rh antigen flag pending serology reconcile",
    "Roll-up narrative for drug or food hypersensitivity alerting",
    "Visit modality bucket OPD IPD Emergency roll-up shorthand",
    "Legal entity campus node anchor for cost allocation",
    "Internal admitting department mnemonic not national display name",
    "First clinician touch datetime for outpatient episode",
    "Inpatient admission instant when converted else blank text",
    "Medically finalized discharge instant when inpatient else blank",
    "Emergency acuity ordinal following local triage ladder",
    "Compressed chief complaint free text excerpt",
    "Abbreviated subjective history aligned to documentation policy",
    "Attending clinician national practice license plaintext",
    "Attending clinician attest display string",
    "Pipe-delimited consult specialty roster draft",
    "Principal discharge ICD10 code with dot delimiter",
    "Pipe-delimited secondary ICD10 list without deterministic order",
    "Primary CM3 operative procedure single row",
    "Supplemental ancillary CM3 procedure bundle pipe joined",
    "Draft DRG group prior payer adjudication",
    "Bundled-payment pilot sentinel 0 no 1 yes",
    "Admission source national reporting crosswalk token",
    "Discharge disposition crosswalk enumerated code",
    "Continuous inpatient elapsed hours fractional emergency blank",
    "Monetary billed charges integer minor currency units",
    "Primary insurance statutory plan category bucket",
    "Secondary payer placeholder when stacked coverage applies",
    "Estimated patient cash responsibility integer minors",
    "Latest structured standing height measurement centimeters",
    "Latest structured body mass measurement kilograms",
    "Latest non-invasive systolic pressure millimeters mercury",
    "Paired latest diastolic pressure millimeters mercury",
    "Latest documented pulse beats per minute",
    "Latest respirations per minute nursing capture",
    "Latest peripheral saturation percent presumed room-air context",
    "Latest core-adjacent temperature degrees Celsius singular reading",
]

HEADERS_FYMX = [
    "FBLYLSH_LINK",
    "MRN_STABLE",
    "BRJZLSH",
    "ITEM_CODE_INT",
    "ITEM_NAME_DISP",
    "CHARGE_CAT",
    "QTY_DETAIL",
    "UNIT_PRICE_FEN",
    "LINE_AMT_FEN",
    "EXE_DEPT_DM",
    "EXE_PHYS_NAME",
    "BILL_EVT_TS",
]

COMMENTS_FYMX = [
    "Charge detail surrogate loosely coupled to episode header surrogate",
    "MPI identifier redundant copy aligning to master row",
    "Foreign visit surrogate required for referential coherence",
    "Internal chargemaster surrogate integer primary key facet",
    "Billing item prose label duplicated from master for invoice PDF",
    "High-level rollup DRUG LAB IMAGING BED SERVICE enumerated",
    "Billable quantity with controlled fractional precision digits",
    "Unit price denominated integer minor yuan units",
    "Line extension amount inclusive of pre-tax facility ledger totals",
    "Performing revenue center mnemonic accountable for throughput",
    "Performing clinician or technician display string plaintext",
    "Charge occurrence compact timestampYYYYMMDDHHMMSS",
]


def random_mobile_sample() -> str:
    prefix = RNG.randint(30, 99)
    suffix = RNG.randint(0, 999_999_999)
    return f"1{prefix}{suffix:09d}"


def random_id_tail_four() -> str:
    return f"{RNG.randint(0, 9999):04d}"


def build_mzjz_rows(row_count: int = 42) -> list[list[object]]:
    """Return synthetic data rows excluding header commentary rows."""

    base_clock = datetime(2025, 10, 8, 7, 30, 0)
    grid: list[list[object]] = []
    for i in range(row_count):
        episode_id = 880_000_601 + i * 137
        outpat_chart = 250_009_010 + i * 29
        mrn_val = 6_001_080_900 + i * 883

        gender_digit = RNG.choice(["1", "2", "9"])
        birth_int = int(
            datetime(
                1956 + i % 44,
                ((i * 5) % 12) + 1,
                max(1, (i % 24) + 1),
            ).strftime("%Y%m%d")
        )

        outpatient_first_seen = base_clock + timedelta(days=i % 38, minutes=RNG.randint(0, 420))
        is_inpatient = i % 5 == 0
        is_emergency = (i % 7 == 0) and not is_inpatient

        admit_readable = ""
        discharge_readable = ""
        if is_inpatient:
            admit = outpatient_first_seen + timedelta(hours=RNG.randint(10, 60))
            disch = admit + timedelta(days=RNG.randint(3, 12), hours=RNG.randint(0, 20))
            admit_readable = admit.strftime("%Y-%m-%d %H:%M:%S")
            discharge_readable = disch.strftime("%Y-%m-%d %H:%M:%S")

        if is_emergency:
            visit_bucket = "EMG"
        elif is_inpatient:
            visit_bucket = "IPD"
        else:
            visit_bucket = "OPD"

        triage_score = RNG.randint(1, 5) if visit_bucket == "EMG" else ""
        dept_stub = f"DEPT-{(i % 16) + 1:02d}"
        contact_pick = RNG.choice(
            ["Alex Carter proxy", "Robin Lee guardian", "Jamie Ortiz emergency contact"]
        )
        display_name = (
            f"SYNTH_PAT_ALPHA_{i + 1:03d}" if i % 3 == 0 else f"SYNTH_PAT_BETA_{i + 1:03d}"
        )

        allergy_line = ""
        if i % 11 == 0:
            allergy_line = "Documented penicillin-class rapid urticaria contraindication"
        if i % 13 == 0:
            allergy_line = (allergy_line + " ; " + "Vancomycin infusion hold per pharmacy").strip(" ;")

        dx_primary_pick = RNG.choice(["E11.603", "I10", "N18.5", "J18.903", "K80.20"])
        dx_secondary_pipe = RNG.choice(["E87.603|N17.931", "Z51.803|Z51.507", "I25.903"])

        license_body = RNG.randint(110_000, 650_000)
        practitioner_license_number = f"CN-GZ-{license_body}-{3800 + i}"
        practitioner_display = RNG.choice(
            ["Dr. Morgan Hale", "Dr. Priya Desai", "Dr. Eli Vance", "Dr. Dana Frost", "Dr. Luis Ortega"]
        )

        zy_hours = round(RNG.uniform(36.0, 228.8), 1) if is_inpatient else ""
        total_charge_cent = RNG.randint(28_900, 5_992_700) if is_inpatient else RNG.randint(2_990, 198_880)
        self_pay_estimate = RNG.randint(0, max(1, total_charge_cent // 4))

        height_cm = round(RNG.uniform(152.8, 189.7), 1)
        weight_kg = round(RNG.uniform(46.0, 106.9), 1)
        sbp = RNG.randint(98, 169)
        dbp = RNG.randint(55, 99)
        hr = RNG.randint(56, 122)
        resp = RNG.randint(12, 28)
        ox = RNG.randint(91, 99)
        temp_celsius = round(RNG.uniform(36.05, 39.08), 1)

        drg_pick = RNG.choice(["ES21", "GB25", "NS15", "BLANK_DRAFT"])
        drg_publish = "" if drg_pick == "BLANK_DRAFT" else drg_pick

        main_proc = RNG.choice(["80.8701", "99.7903", "", "93.9621"])

        bundled_flag = RNG.choice(["0", "1"]) if visit_bucket != "OPD" else "0"

        grid.append(
            [
                episode_id,
                outpat_chart,
                mrn_val,
                display_name,
                gender_digit,
                birth_int,
                random_id_tail_four(),
                random_mobile_sample(),
                f"Demo Ave unit {RNG.randint(1, 99)} virtual tower {RNG.randint(1, 28)}",
                "310115" if i % 2 == 0 else "440305",
                contact_pick,
                random_mobile_sample(),
                RNG.choice(["A", "B", "AB", "O", "UNK"]),
                RNG.choice(["POS", "NEG", "PEND"]),
                allergy_line,
                visit_bucket,
                "ORG01-EASTBLOCK",
                dept_stub,
                outpatient_first_seen.strftime("%Y-%m-%d %H:%M:%S"),
                admit_readable,
                discharge_readable,
                triage_score,
                (
                    "Intermittent exertional chest tightness x3 weeks"
                    if i % 2 == 0
                    else "Episodic abdominal pain with nausea x4 weeks"
                ),
                "Prior outpatient therapy elsewhere with fluctuating symptoms; escalated for specialist review",
                practitioner_license_number,
                practitioner_display,
                "|".join(
                    RNG.sample(
                        ["CS-IMM", "CS-CARDIO", "CS-NEPH", "LAB-MICRO"], k=RNG.randint(1, 3)
                    )
                ),
                dx_primary_pick,
                dx_secondary_pipe,
                main_proc,
                "93.9621|90.5960" if main_proc else "",
                drg_publish,
                bundled_flag,
                RNG.choice(["2", "3", "9"]),
                RNG.choice(["1", "2", "3", "9"]),
                zy_hours,
                total_charge_cent,
                RNG.choice(["MI-URB_EMP", "MI-RURAL", "MI-URB_RES", "SELFPAY"]),
                "EC-SUP_NONE" if i % 4 else "EC-SUP_COMM",
                self_pay_estimate,
                height_cm,
                weight_kg,
                sbp,
                dbp,
                hr,
                resp,
                ox,
                temp_celsius,
            ]
        )
    return grid


def build_fymx_rows(
    mz_rows: list[list[object]],
    lines_per_visit: tuple[int, int] = (1, 6),
) -> list[list[object]]:
    """Charge-detail lines keyed to synthetic encounters."""

    lines: list[list[object]] = []
    ledger_seq = 9_991_020_001
    for row in mz_rows:
        episode_id = row[0]
        mrn = row[2]
        n_lines = RNG.randint(lines_per_visit[0], lines_per_visit[1])
        for _ in range(n_lines):
            ledger_seq += RNG.randint(1, 51)
            item_code = RNG.randint(10_090, 99_981)
            item_name = RNG.choice(
                [
                    "Peripheral IV maintenance surcharge",
                    "Level-III inpatient evaluation management",
                    "Serum creatinine enzymatic assay",
                    "CT head with contrast 3D reformations",
                    "Ambroxol HCl injection 2mL",
                    "Digital radiography chest PA and lateral",
                ]
            )
            cat = RNG.choice(["DRUG", "LAB", "IMAGING", "BED", "SERVICE"])
            qty = round(RNG.uniform(1.0, 6.25), RNG.choice([2, 3]))
            unit_price = RNG.randint(120, 18_990)
            line_amt = int(round(unit_price * float(qty)))
            exe_dept = f"EXE-DEPT-{RNG.randint(11, 99)}"
            phys = RNG.choice(["Tech Jordan Park", "Rad Casey Kim", "Lab Avery Fox", None, ""])
            phys_cell = phys or ""
            bill_ts = datetime(2025, 11, 2, RNG.randint(6, 22), RNG.randint(0, 59), 0).strftime("%Y%m%d%H%M%S")

            lines.append(
                [
                    ledger_seq,
                    mrn,
                    episode_id,
                    item_code,
                    item_name,
                    cat,
                    qty,
                    unit_price,
                    line_amt,
                    exe_dept,
                    phys_cell,
                    bill_ts,
                ]
            )
    return lines


def main() -> None:
    mz_grid = build_mzjz_rows(42)
    line_grid = build_fymx_rows(mz_grid)

    df_mz = pd.DataFrame(mz_grid, columns=HEADERS_MZJZ)
    df_fy = pd.DataFrame(line_grid, columns=HEADERS_FYMX)

    mz_frame = pd.concat(
        [
            pd.DataFrame([HEADERS_MZJZ], columns=HEADERS_MZJZ),
            pd.DataFrame([COMMENTS_MZJZ], columns=HEADERS_MZJZ),
            df_mz,
        ],
        ignore_index=True,
    )

    fy_frame = pd.concat(
        [
            pd.DataFrame([HEADERS_FYMX], columns=HEADERS_FYMX),
            pd.DataFrame([COMMENTS_FYMX], columns=HEADERS_FYMX),
            df_fy,
        ],
        ignore_index=True,
    )

    _PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(_OUT_FIXTURE, engine="openpyxl") as xlw:
        mz_frame.to_excel(xlw, sheet_name="HIS_MZJZ_BRIDGE", index=False, header=False)
        fy_frame.to_excel(xlw, sheet_name="HIS_FYMX_SLICE", index=False, header=False)

    pub_xlsx = _PUBLIC_DIR / "demo_hospital_ehr_messy_multi_sheet.xlsx"
    shutil.copy2(_OUT_FIXTURE, pub_xlsx)

    std_src = _HERE / "std_patient_clinical_hub.json"
    if std_src.is_file():
        shutil.copy2(std_src, _PUBLIC_DIR / "std_patient_clinical_hub.json")

    print(f"Wrote {_OUT_FIXTURE.relative_to(_REPO)}")
    print(f"Copied demo assets into {pub_xlsx.relative_to(_REPO)}")


if __name__ == "__main__":
    main()
