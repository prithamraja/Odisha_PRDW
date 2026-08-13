"""
Gates 3 and 4 of AP_ASK_RERANK_HANDOFF.md — PM-KISAN as the seventh scheme,
end to end through route() and through direct SQL, against the real flat drop.

  cd Chatbot/backend
  DATA_DIR=<repo>/RTGS_Data/flat python pmkisan_gates.py

Gate 3 checks routing + binding + execution for the PM-KISAN vocabulary,
including the regression guard that "Which PM-KISAN farmers are not in
Sericulture?" still binds scheme=Sericulture (S01) rather than scheme=PM-KISAN.
Gate 4 checks the seven-scheme semantics the SQL edits are supposed to produce,
and that the KEEP-SIX templates did NOT pick up a PM-KISAN leg.
"""
import io
import os
import sys

from dotenv import load_dotenv

load_dotenv()

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from openai import OpenAI

from db_factory import get_adapter
from query_router.dashboard_catalog import DASHBOARD_CATALOG
from query_router.entity_validator import EntityValidator
from query_router.router import route
from query_router.template_catalog import TEMPLATE_CATALOG
from query_router.vector_retriever import VectorRetriever

FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(f"{label}: {detail}")


def entities(result) -> dict:
    return {e.slot_name: e.resolved_value for e in (result.entities or [])}


def main() -> None:
    adapter = get_adapter()
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    validator = EntityValidator(adapter)
    retriever = VectorRetriever(client, DASHBOARD_CATALOG, TEMPLATE_CATALOG)

    def ask(question: str):
        return route(
            question,
            validator=validator,
            openai_client=client,
            cache_conn=adapter,
            dashboard_results={},
            template_map=dict(TEMPLATE_CATALOG),
            dashboard_questions={},
            retriever=retriever,
        )

    def sql(query: str):
        rel = adapter.execute(query)
        cols = rel.description
        return [dict(zip(cols, r)) for r in rel.fetchall()]

    # ── Gate 3 — PM-KISAN end to end ─────────────────────────────────────────
    print("\n=== Gate 3 — PM-KISAN end to end ===")

    r = ask("Which farmers are in PM-KISAN but not in Fisheries?")
    e = entities(r)
    check("S02 / PM-KISAN minus Fisheries routes to S02", r.query_id == "S02",
          f"got {r.query_id}")
    check("  binds scheme=PM-KISAN, scheme_2=Fisheries",
          e.get("scheme") == "PM-KISAN" and e.get("scheme_2") == "Fisheries", str(e))
    check("  executes and returns plausible rows", bool(r.result), f"{len(r.result or [])} rows")

    r = ask("Which farmers are in Fisheries but not in PM-KISAN?")
    e = entities(r)
    check("S02 / Fisheries minus PM-KISAN routes to S02", r.query_id == "S02",
          f"got {r.query_id}")
    check("  binds scheme=Fisheries, scheme_2=PM-KISAN",
          e.get("scheme") == "Fisheries" and e.get("scheme_2") == "PM-KISAN", str(e))
    check("  non-empty (the deliberate orphan residue)", bool(r.result),
          f"{len(r.result or [])} rows")

    r = ask("Which farmers are registered in PM KISAN?")
    e = entities(r)
    check("S07 / unhyphenated alias routes to S07", r.query_id == "S07", f"got {r.query_id}")
    check("  alias 'PM KISAN' resolves to PM-KISAN", e.get("scheme") == "PM-KISAN", str(e))
    check("  returns the roster", bool(r.result), f"{len(r.result or [])} rows")

    r = ask("Which PM-KISAN farmers are not in Sericulture?")
    e = entities(r)
    check("REGRESSION GUARD: routes to S01", r.query_id == "S01", f"got {r.query_id}")
    check("  binds scheme=Sericulture, NOT PM-KISAN",
          e.get("scheme") == "Sericulture", str(e))

    for q in ("Which Aadhaar numbers in PM-KISAN do not exist in PM-KISAN?",
              "Which Aadhaar numbers in PMKISAN do not exist in PM-KISAN?"):
        r = ask(q)
        check(f"degenerate executes without error: {q[:46]}...",
              r.query_id is not None and r.result is not None,
              f"tier={r.tier.value} query_id={r.query_id} "
              f"rows={len(r.result) if r.result is not None else 'None'}")
        check("  and returns empty, as it must by construction", not r.result,
              f"{len(r.result or [])} rows")

    # ── Gate 4 — seven-scheme semantics ──────────────────────────────────────
    print("\n=== Gate 4 — seven-scheme semantics ===")

    r = ask("Which farmers are enrolled in exactly 7 schemes?")
    e = entities(r)
    check("Q114 accepts scheme_count=7", r.query_id == "Q114" and e.get("scheme_count") == "7",
          f"{r.query_id} {e}")
    rows = sql(TEMPLATE_CATALOG["Q114"]["sql_template"].replace("?", "7"))
    all_seven = all("PM-KISAN" in (row.get("scheme_list") or "") for row in rows)
    check("  every 7-scheme farmer is on the roster and in all six AP schemes",
          bool(rows) and all_seven, f"{len(rows)} farmers, all list PM-KISAN: {all_seven}")

    n6_before = sql("""
        WITH sch AS (
          SELECT "aadharno" AS aadhaar, 'Agriculture' AS scheme FROM agriculture
          UNION SELECT "EXTN_AADHARNO", 'Horticulture' FROM horticulture_apmip
          UNION SELECT "aadhar_no",     'Fisheries'    FROM fisheries
          UNION SELECT "aadhaar_no",    'Sericulture'  FROM sericulture
          UNION SELECT "AADHAAR_NO",    'MARKFED'      FROM markfed
          UNION SELECT "Aadhar_no",     'RySS'         FROM ryss)
        SELECT COUNT(*) AS n FROM (
          SELECT aadhaar FROM sch GROUP BY aadhaar HAVING COUNT(DISTINCT scheme) = 6)""")[0]["n"]
    check("  the six-AP-scheme population is the same size as the 7-scheme one",
          n6_before == len(rows), f"6-of-6: {n6_before}, 7-of-7: {len(rows)}")

    # S04: every roster member's scheme count is exactly +1 versus the six-scheme baseline
    delta = sql("""
        WITH sch6 AS (
          SELECT "aadharno" AS aadhaar, 'Agriculture' AS scheme FROM agriculture
          UNION SELECT "EXTN_AADHARNO", 'Horticulture' FROM horticulture_apmip
          UNION SELECT "aadhar_no",     'Fisheries'    FROM fisheries
          UNION SELECT "aadhaar_no",    'Sericulture'  FROM sericulture
          UNION SELECT "AADHAAR_NO",    'MARKFED'      FROM markfed
          UNION SELECT "Aadhar_no",     'RySS'         FROM ryss),
        sch7 AS (SELECT * FROM sch6 UNION SELECT "aadhaar_no", 'PM-KISAN' FROM pm_kisan),
        c6 AS (SELECT aadhaar, COUNT(DISTINCT scheme) n FROM sch6 GROUP BY aadhaar),
        c7 AS (SELECT aadhaar, COUNT(DISTINCT scheme) n FROM sch7 GROUP BY aadhaar)
        SELECT COUNT(*) AS rostered,
               SUM(CASE WHEN c7.n = COALESCE(c6.n, 0) + 1 THEN 1 ELSE 0 END) AS plus_one
        FROM pm_kisan p
        JOIN c7 ON c7.aadhaar = p."aadhaar_no"
        LEFT JOIN c6 ON c6.aadhaar = p."aadhaar_no" """)[0]
    check("S04: every roster member's scheme count is exactly +1",
          delta["rostered"] == delta["plus_one"],
          f"{delta['plus_one']}/{delta['rostered']}")

    top = sql(TEMPLATE_CATALOG["S04"]["sql_template"].replace("?", "10"))
    check("S04: top-ranked farmers now show a scheme count of 7",
          bool(top) and top[0]["schemes"] == 7, f"top count = {top[0]['schemes'] if top else 'n/a'}")

    # F12 for a farmer on the roster
    name = sql("""SELECT "name" FROM pm_kisan p WHERE EXISTS
                  (SELECT 1 FROM agriculture a WHERE a."aadharno" = p."aadhaar_no")
                  LIMIT 1""")[0]["name"]
    f12 = sql(TEMPLATE_CATALOG["F12"]["sql_template"].replace("?", f"'{name}'"))
    pmk = [row for row in f12 if str(row["scheme"]).startswith("PM-KISAN")]
    check("F12: includes a PM-KISAN row labelled latest-installment-only",
          len(pmk) == 1 and "latest installment" in pmk[0]["scheme"],
          f"{name}: {[row['scheme'] for row in f12]}")
    if pmk:
        credited = sql(f"""SELECT SUM("last_amount_credited") AS a FROM pm_kisan
                           WHERE UPPER(TRIM("name")) = UPPER(TRIM('{name}'))""")[0]["a"]
        check("  and that row equals the roster's last_amount_credited",
              abs(float(pmk[0]["amount"]) - float(credited)) < 0.01,
              f"{pmk[0]['amount']} vs {credited}")

    # KEEP-SIX verification.
    #
    # The handoff's gate reads "G35-S still returns a non-empty list and Q015's
    # pct_reached stays < 100; if either degenerates, PM-KISAN leaked". On this
    # data drop that test cannot distinguish a leak from the data: all 1,100
    # roster farmers are already in at least one of the six state schemes, so
    # G35-S returns 0 rows and Q015 reads 100.0% BEFORE any change here (verified
    # against the pre-patch catalog). So the leak test is made structural — the
    # six-scheme set in these templates must still be exactly six — and the
    # degeneracy is reported as the data finding it is.
    g35 = sql(TEMPLATE_CATALOG["G35-S"]["sql_template"])
    q015 = sql(TEMPLATE_CATALOG["Q015"]["sql_template"])[0]
    unreached_six = sql("""
        WITH ap AS (
          SELECT "aadharno" AS aadhaar FROM agriculture
          UNION SELECT "EXTN_AADHARNO" FROM horticulture_apmip
          UNION SELECT "aadhar_no"     FROM fisheries
          UNION SELECT "aadhaar_no"    FROM sericulture
          UNION SELECT "AADHAAR_NO"    FROM markfed
          UNION SELECT "Aadhar_no"     FROM ryss)
        SELECT COUNT(*) AS n FROM pm_kisan p
        WHERE p."aadhaar_no" NOT IN (SELECT aadhaar FROM ap WHERE aadhaar IS NOT NULL)""")[0]["n"]
    check("KEEP-SIX: G35-S matches the six-state-scheme truth exactly (no leak)",
          len(g35) == unreached_six,
          f"G35-S {len(g35)} rows vs six-scheme truth {unreached_six}")
    check("KEEP-SIX: Q015 pct_reached matches the six-state-scheme truth (no leak)",
          abs(float(q015["reached_by_state_scheme"]) - (1100 - unreached_six)) < 0.5,
          f"reached {q015['reached_by_state_scheme']}, pct {q015['pct_reached']}")
    if unreached_six == 0:
        print("  NOTE  G35-S is empty and Q015 reads 100% because this data drop has "
              "100% state-scheme convergence — a property of the data, not of this change.")

    for qid in ("G35-S", "G35-D", "G35-M", "Q015", "Q029", "Q059", "Q112",
                "Q135", "M06", "Q129", "Q128", "G37-S", "G37-D", "G37-M", "Q134",
                "Q126", "Q148", "Q152"):
        leaked = "'PM-KISAN'" in TEMPLATE_CATALOG[qid]["sql_template"]
        check(f"KEEP-SIX: no PM-KISAN leg leaked into {qid}", not leaked)

    print("\n" + ("ALL GATES PASS" if not FAILURES else f"{len(FAILURES)} FAILURE(S)"))
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
