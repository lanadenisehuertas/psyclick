"""
report_exporter.py — PsyClick
Generates a professional HTML clinical report that opens in the browser
and can be printed to PDF via Ctrl+P. No external dependencies required.
"""

import json, os, webbrowser, tempfile
from datetime import datetime


def _flag_color(flag):
    return {"GREEN": "#10B981", "AMBER": "#F59E0B", "RED": "#EF4444"}.get(flag, "#64748B")

def _flag_bg(flag):
    return {"GREEN": "#D1FAE5", "AMBER": "#FEF3C7", "RED": "#FEE2E2"}.get(flag, "#F1F5F9")

def _phq(s):
    if s <= 4: return "Minimal depression"
    if s <= 9: return "Mild depression"
    if s <= 14: return "Moderate depression"
    if s <= 19: return "Moderately severe depression"
    return "Severe depression"

def _gad(s):
    if s <= 4: return "Minimal anxiety"
    if s <= 9: return "Mild anxiety"
    if s <= 14: return "Moderate anxiety"
    return "Severe anxiety"

def _t2_interp(t2, thr):
    if thr == 0 or thr == float("inf"):
        return "Insufficient baseline data for comparison."
    ratio = t2 / thr
    if ratio <= 1.0:
        return f"Within normal range ({ratio:.2f}× threshold). No statistical anomaly detected."
    if ratio <= 1.5:
        return f"Moderately elevated ({ratio:.2f}× threshold). Warrants clinical attention."
    return f"Significantly elevated ({ratio:.2f}× threshold). Strong deviation from personal baseline."

def _psi_interp(psi):
    if psi < 0.5: return "Within normal range. No significant psychomotor slowing detected."
    if psi < 2.0: return "Mildly elevated. Some psychomotor slowing observed — extended key press intervals and pausing."
    if psi < 4.0: return "Moderately elevated. Clear psychomotor slowing pattern consistent with depressive inhibition."
    return "Severely elevated. Marked psychomotor slowing — clinically significant, consistent with severe depression or fatigue."

def _pai_interp(pai):
    if pai < 0.5: return "Within normal range. No psychomotor agitation detected."
    if pai < 2.0: return "Mildly elevated. Slight cursor irregularity and typing inconsistency."
    if pai < 4.0: return "Moderately elevated. Erratic cursor movements and keystroke variance consistent with anxiety-driven hyperarousal."
    return "Severely elevated. Highly erratic psychomotor pattern — consistent with acute anxiety, panic, or significant agitation."

def _group_name(gid):
    return {1: "Time Pressure & Workload", 2: "Interpersonal Friction",
            3: "Academic & Performance Pressure", 4: "Self-Evaluation & Identity"}.get(gid, f"Group {gid}")


def generate_html_report(data):
    """Generate HTML report string from result data dict."""
    ae    = data.get("analysis") or {}
    flag  = ae.get("flag", "GREEN")
    t2    = ae.get("t2_score", 0.0)
    thr   = ae.get("t2_threshold", 0.0)
    psi   = ae.get("psi", 0.0)
    pai   = ae.get("pai", 0.0)
    conf  = ae.get("confidence", 0.0)
    label = ae.get("label", "Normal")
    rat   = ae.get("rationale", "")
    phq   = data.get("phq", {}).get("score", 0)
    gad   = data.get("gad", {}).get("score", 0)
    pid   = data.get("student_id", "—")
    ts    = data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M"))
    vis   = data.get("visuals", {})
    snaps = vis.get("question_snapshots", [])
    dom   = vis.get("domain_t2", {})

    fc = _flag_color(flag)
    fb = _flag_bg(flag)

    # Build per-question table rows
    snap_rows = ""
    for s in snaps:
        sc = _flag_color(s.get("flag","GREEN"))
        hover_txt = ", ".join([f'"{h["word"]}" ({h["dwell_ms"]:.0f}ms)'
                               for h in s.get("hover_words", [])[:3]])
        snap_rows += f"""
        <tr>
          <td><strong style="color:{_flag_color(s.get('flag','GREEN'))}">{s.get('item_id','?')}</strong></td>
          <td>{s.get('group_name','')[:30]}</td>
          <td>{s.get('level','?')}</td>
          <td>{s.get('t2_score',0):.3f}</td>
          <td>{s.get('psi',0):.3f}</td>
          <td>{s.get('pai',0):.3f}</td>
          <td>{s.get('flight_time',0)*1000:.0f} ms</td>
          <td>{s.get('pause_freq',0):.3f}</td>
          <td><span style="background:{sc};color:white;padding:2px 8px;border-radius:10px;font-size:11px">{s.get('flag','GREEN')}</span></td>
          <td style="font-size:11px;color:#64748B">{hover_txt or "—"}</td>
        </tr>"""

    # Domain bars (inline SVG)
    domain_svg = ""
    if dom:
        colors = {1:"#3B82F6",2:"#8B5CF6",3:"#10B981",4:"#EF4444"}
        names  = {1:"Workload",2:"Interpersonal",3:"Academic",4:"Self-Eval"}
        mv     = max(dom.values()) if dom else 1
        for i, (gid, val) in enumerate(sorted(dom.items())):
            col  = colors.get(int(gid),"#888")
            nm   = names.get(int(gid),"")
            pct  = min(int((val/mv)*100), 100)
            domain_svg += f"""
            <div style="margin-bottom:10px">
              <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px">
                <span style="font-weight:600;color:{col}">{nm}</span>
                <span style="color:#64748B">T² = {val:.3f}</span>
              </div>
              <div style="background:#E2E8F0;border-radius:4px;height:14px">
                <div style="background:{col};width:{pct}%;height:100%;border-radius:4px"></div>
              </div>
            </div>"""

    now = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PsyClick Clinical Report — {pid}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #F8FAFC; color: #1E293B; }}
  .page {{ max-width: 900px; margin: 0 auto; padding: 40px 32px; }}
  .header {{ display:flex; justify-content:space-between; align-items:center;
             border-bottom: 3px solid #8B5CF6; padding-bottom: 20px; margin-bottom: 28px; }}
  .logo {{ font-size: 28px; font-weight: 800; color: #8B5CF6; }}
  .logo span {{ font-size:12px; color:#64748B; display:block; font-weight:400; margin-top:2px; }}
  .meta {{ text-align:right; font-size:12px; color:#64748B; }}
  .meta strong {{ color:#1E293B; }}
  .banner {{ padding: 18px 22px; border-radius: 12px; margin-bottom: 24px;
             background: {fb}; border-left: 5px solid {fc}; }}
  .banner h2 {{ color: {fc}; font-size: 18px; margin-bottom: 4px; }}
  .banner p {{ color: #475569; font-size: 13px; }}
  .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }}
  .grid4 {{ display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 12px; margin-bottom: 20px; }}
  .card {{ background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 18px 20px; }}
  .card h3 {{ font-size: 13px; color: #64748B; font-weight: 600; margin-bottom: 6px; text-transform: uppercase; letter-spacing: .4px; }}
  .metric-val {{ font-size: 28px; font-weight: 800; }}
  .metric-sub {{ font-size: 11px; color: #64748B; margin-top: 2px; }}
  .interp {{ font-size: 12px; color: #475569; margin-top: 8px; padding-top: 8px;
             border-top: 1px solid #F1F5F9; line-height: 1.5; }}
  .section {{ background: white; border: 1px solid #E2E8F0; border-radius: 12px;
              padding: 20px 22px; margin-bottom: 20px; }}
  .section h2 {{ font-size: 15px; font-weight: 700; color: #1E293B; margin-bottom: 12px; }}
  .section p {{ font-size: 13px; color: #475569; line-height: 1.6; }}
  table {{ width:100%; border-collapse:collapse; font-size:12px; }}
  th {{ background:#F8FAFC; text-align:left; padding:8px 10px; color:#64748B;
        font-weight:600; border-bottom:1px solid #E2E8F0; }}
  td {{ padding:8px 10px; border-bottom:1px solid #F1F5F9; vertical-align:middle; }}
  tr:last-child td {{ border-bottom: none; }}
  .rec {{ display:flex; gap:14px; padding:12px 0; border-bottom:1px solid #F1F5F9; }}
  .rec:last-child {{ border-bottom:none; }}
  .rec-num {{ background:#3B82F6; color:white; border-radius:50%; width:26px; height:26px;
              min-width:26px; display:flex; align-items:center; justify-content:center;
              font-weight:700; font-size:12px; margin-top:1px; }}
  .rec-title {{ font-weight:700; font-size:13px; color:#1E293B; margin-bottom:4px; }}
  .rec-body {{ font-size:12px; color:#475569; line-height:1.55; }}
  .score-bar-wrap {{ margin-bottom:12px; }}
  .score-label {{ display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px; }}
  .score-bar {{ background:#E2E8F0; border-radius:4px; height:10px; }}
  .score-fill {{ height:100%; border-radius:4px; background:#EF4444; }}
  .tag {{ display:inline-block; padding:2px 10px; border-radius:10px; font-size:11px;
          font-weight:600; margin-right:6px; }}
  .footer {{ margin-top:32px; padding-top:16px; border-top:1px solid #E2E8F0;
             font-size:11px; color:#94A3B8; text-align:center; }}
  @media print {{
    body {{ background: white; }}
    .page {{ padding: 20px; }}
    .no-print {{ display: none !important; }}
  }}
</style>
</head>
<body>
<div class="page">

  <!-- HEADER -->
  <div class="header">
    <div>
      <div class="logo">Ψ PsyClick<span>Clinical Decision Support System</span></div>
    </div>
    <div class="meta">
      <strong>Patient ID:</strong> {pid}<br>
      <strong>Session Date:</strong> {ts}<br>
      <strong>Report Generated:</strong> {now}<br>
      <span style="background:#EDE9FE;color:#6D28D9;padding:2px 8px;border-radius:8px;font-size:11px">CONFIDENTIAL — FOR CLINICIAN USE ONLY</span>
    </div>
  </div>

  <!-- OVERALL STATUS BANNER -->
  <div class="banner">
    <h2>OVERALL STATUS: {flag} — {label}</h2>
    <p>{rat}</p>
  </div>

  <!-- ROW 1: Screening + Fuzzy -->
  <div class="grid2">
    <div class="card">
      <h3>PHQ-9 / GAD-7 Screening</h3>
      <div class="score-bar-wrap">
        <div class="score-label">
          <span>PHQ-9 Depression</span>
          <strong style="color:#EF4444">{phq}/27 — {_phq(phq)}</strong>
        </div>
        <div class="score-bar"><div class="score-fill" style="width:{min(phq/27*100,100):.0f}%"></div></div>
      </div>
      <div class="score-bar-wrap">
        <div class="score-label">
          <span>GAD-7 Anxiety</span>
          <strong style="color:#EF4444">{gad}/21 — {_gad(gad)}</strong>
        </div>
        <div class="score-bar"><div class="score-fill" style="width:{min(gad/21*100,100):.0f}%"></div></div>
      </div>
    </div>
    <div class="card">
      <h3>Fuzzy Logic Classification</h3>
      <div style="font-size:24px;font-weight:800;color:{fc}">{label}</div>
      <div style="font-size:13px;color:#64748B;margin:4px 0">Confidence: {int(conf*100)}%</div>
      <div class="interp">The fuzzy classifier combines T², PSI, and PAI into a graded membership
      classification. Higher confidence means the pattern more clearly matches the labeled category.</div>
    </div>
  </div>

  <!-- ROW 2: 4 Metric cards with interpretations -->
  <div class="grid2">
    <div class="card">
      <h3>T² Score (Hotelling's T²)</h3>
      <div class="metric-val" style="color:#EF4444">{t2:.3f}</div>
      <div class="metric-sub">F-threshold (UCL): {thr:.2f if thr != float('inf') else 'N/A'}</div>
      <div class="interp">
        <strong>What this means:</strong> {_t2_interp(t2, thr)}<br><br>
        <strong>Clinical note:</strong> T² measures how far the patient's combined behavioral fingerprint
        has drifted from their own calibration baseline. A score above the F-threshold indicates a
        statistically significant change in psychomotor behavior during the emotional task — not just
        noise, but a genuine shift detectable against their personal norm.
      </div>
    </div>
    <div class="card">
      <h3>PSI — Psychomotor Slowing Index</h3>
      <div class="metric-val" style="color:#3B82F6">{psi:.3f}</div>
      <div class="metric-sub">Composed of: flight time, dwell time, pause frequency</div>
      <div class="interp">
        <strong>What this means:</strong> {_psi_interp(psi)}<br><br>
        <strong>Clinical note:</strong> PSI quantifies motor inhibition — the tendency to press keys
        more slowly, hold them longer, and pause more frequently between words. This mirrors the
        observable psychomotor retardation clinicians look for in depression. The system captures it
        millisecond-by-millisecond across all 12 prompts.
      </div>
    </div>
    <div class="card">
      <h3>PAI — Psychomotor Agitation Index</h3>
      <div class="metric-val" style="color:#8B5CF6">{pai:.3f}</div>
      <div class="metric-sub">Composed of: jerk, path entropy, error rate, cursor velocity</div>
      <div class="interp">
        <strong>What this means:</strong> {_pai_interp(pai)}<br><br>
        <strong>Clinical note:</strong> PAI quantifies motor restlessness — cursor jerkiness, erratic
        movement paths, and increased correction errors. This corresponds to the motor restlessness and
        impulsivity patterns associated with anxiety and agitated states. Unlike overt fidgeting, these
        micro-patterns in cursor dynamics are often below the threshold of clinical observation.
      </div>
    </div>
    <div class="card">
      <h3>Domain-Segmented T² Profile</h3>
      {domain_svg if domain_svg else '<p style="color:#94A3B8;font-size:12px">No domain data available.</p>'}
      <div class="interp" style="margin-top:8px">The stressor domain with the highest T² is where
      psychomotor deviation was greatest — indicating the topic area most likely to be the patient's
      primary emotional vulnerability in this session.</div>
    </div>
  </div>

  <!-- PER-QUESTION BIOMETRIC TABLE -->
  <div class="section">
    <h2>Per-Question Biometric Profile</h2>
    <p style="margin-bottom:12px;font-size:12px;color:#64748B">
      Each row represents one emotional response item. Flight time = average inter-keystroke interval.
      Pause/s = cursor pause events per second. Hover words = words the cursor lingered on longest before typing.
      Items flagged AMBER or RED indicate that specific question triggered a statistically significant psychomotor shift.
    </p>
    <table>
      <thead>
        <tr>
          <th>Item</th><th>Group</th><th>Lvl</th><th>T²</th><th>PSI</th><th>PAI</th>
          <th>Flight</th><th>Pause/s</th><th>Flag</th><th>Top Hover Words</th>
        </tr>
      </thead>
      <tbody>{snap_rows if snap_rows else '<tr><td colspan="10" style="text-align:center;color:#94A3B8;padding:20px">No per-question data available</td></tr>'}</tbody>
    </table>
  </div>

  <!-- CLINICAL RECOMMENDATIONS -->
  <div class="section">
    <h2>⚠ Clinical Recommendations</h2>
    <p style="font-size:12px;color:#64748B;margin-bottom:14px">
      The following recommendations are generated from the combined psychomotor profile, screening scores,
      and domain-level analysis. They are intended to augment — not replace — clinical judgment.
    </p>
    <div id="recs"></div>
  </div>

  <div class="footer">
    PsyClick Clinical Decision Support System &nbsp;|&nbsp; Generated {now}<br>
    This report is a decision support tool. All clinical conclusions require professional interpretation.
    Not a substitute for a licensed clinician's assessment.
  </div>

</div>

<script>
// Inject recommendations from embedded data
const recs = {json.dumps(_build_recs_for_html(ae, phq, gad, dom, vis.get('level_t2', {})))};
const container = document.getElementById('recs');
recs.forEach((r, i) => {{
  container.innerHTML += `<div class="rec">
    <div class="rec-num">${{i+1}}</div>
    <div><div class="rec-title">${{r.title}}</div><div class="rec-body">${{r.body}}</div></div>
  </div>`;
}});
</script>
</body>
</html>"""
    return html


def _build_recs_for_html(ae, phq, gad, domain_t2, level_t2):
    flag  = ae.get("flag", "GREEN")
    label = ae.get("label", "Normal")
    psi   = ae.get("psi", 0.0)
    pai   = ae.get("pai", 0.0)
    recs  = []

    if flag == "RED":
        recs.append({"title": "🔴 Immediate Safety Assessment Required",
                     "body": f"RED psychomotor flag combined with PHQ-9={phq} and GAD-7={gad} "
                             "warrants an immediate structured risk assessment. Do not defer to next session."})
    elif flag == "AMBER":
        recs.append({"title": "🟡 Prioritized Follow-Up Within 48–72 Hours",
                     "body": "Schedule a structured follow-up. Review flagged stressor domains before next session."})
    else:
        recs.append({"title": "🟢 Routine Monitoring",
                     "body": "Psychomotor indicators within normal range. Continue standard follow-up schedule."})

    if "Retardation" in label or psi > pai:
        recs.append({"title": "🧠 Psychomotor Retardation Pattern — Consider MADRS",
                     "body": f"PSI={psi:.3f} dominates. Motor inhibition pattern consistent with depressive inhibition. "
                             "Assess energy, motivation, and cognitive slowing. Consider MADRS administration."})
    elif "Agitation" in label or pai > psi:
        recs.append({"title": "⚡ Psychomotor Agitation Pattern — Consider HAM-A",
                     "body": f"PAI={pai:.3f} dominates. Motor restlessness consistent with anxiety-driven hyperarousal. "
                             "Explore triggers, sleep, rumination. Consider HAM-A."})
    elif "Mixed" in label:
        recs.append({"title": "🔀 Mixed Psychomotor Disturbance — Consider Bipolar Screen",
                     "body": f"Both PSI={psi:.3f} and PAI={pai:.3f} elevated. Mixed pattern may indicate bipolar spectrum, "
                             "severe MDD with agitation, or acute stress. Consider MDQ or mood episode timeline review."})

    if phq >= 15:
        recs.append({"title": "📋 Severe Depression (PHQ-9)",
                     "body": f"Score {phq}/27. Warrants psychiatric evaluation and consideration of pharmacological intervention."})
    if gad >= 10:
        recs.append({"title": "📋 Significant Anxiety (GAD-7)",
                     "body": f"Score {gad}/21. Explore avoidance behaviors. Consider CBT referral or anxiolytic review."})

    if domain_t2:
        peak = max(domain_t2, key=lambda k: domain_t2[k])
        val  = domain_t2[peak]
        names = {1:"Time Pressure & Workload",2:"Interpersonal Friction",
                 3:"Academic & Performance Pressure",4:"Self-Evaluation & Identity"}
        tips  = {1:"Explore workload management, time anxiety, and boundary-setting.",
                 2:"Explore unresolved conflicts, attachment patterns, and interpersonal triggers.",
                 3:"Explore performance anxiety, perfectionism, and evaluation fear.",
                 4:"Explore self-concept, core beliefs, identity stressors, and self-critical cognitions."}
        if val > 0.3:
            recs.append({"title": f"🎯 Peak Stressor Domain: {names.get(int(peak),'?')}",
                         "body": f"T²={val:.3f} — highest psychomotor deviation in this domain. "
                                 f"{tips.get(int(peak), '')} Prioritize this domain in next session."})

    if level_t2:
        la = level_t2.get("A", 0); lb = level_t2.get("B", 0); lc = level_t2.get("C", 0)
        if lc > lb > la and lc > 0.3:
            recs.append({"title": "📈 Dose-Response Escalation Confirmed",
                         "body": f"T² increases A→B→C (A={la:.2f}, B={lb:.2f}, C={lc:.2f}). "
                                 "Self-evaluative items (Level C) produced strongest signal. "
                                 "Self-concept likely a primary emotional vulnerability."})

    recs.append({"title": "⏱ Review Hover-Word Hesitation Map",
                 "body": "Words where the cursor paused longest before typing indicate topics with highest "
                         "cognitive resistance. These are direct entry points for the therapeutic interview."})
    return recs


def export_report(data, filepath=None):
    """
    Generate the HTML report and save to filepath (or temp file).
    Opens in default browser. Returns the file path.
    """
    html = generate_html_report(data)
    if not filepath:
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        pid  = data.get("student_id", "unknown")
        name = f"PsyClick_Report_{pid}_{ts}.html"
        filepath = os.path.join(os.path.expanduser("~"), "Desktop", name)
        # Fallback if Desktop doesn't exist
        if not os.path.isdir(os.path.dirname(filepath)):
            filepath = os.path.join(tempfile.gettempdir(), name)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    webbrowser.open(f"file:///{filepath.replace(os.sep, '/')}")
    return filepath
