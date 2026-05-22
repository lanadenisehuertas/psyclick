"""
report_exporter.py — PsyClick
Generates a professional HTML clinical report that opens in the browser
and can be printed to PDF via Ctrl+P. No external dependencies required.
"""

import json, os, sys, base64, tempfile
from datetime import datetime


def _logo_b64():
    """Return a data-URI for the PsyClick logo, or empty string if not found."""
    exe_dir = os.path.dirname(os.path.abspath(getattr(sys, 'executable', __file__)))
    candidates = [
        # project root  (dev)
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images', 'LOGOggg.png'),
        # PyInstaller frozen bundle
        os.path.join(getattr(sys, '_MEIPASS', ''), 'images', 'LOGOggg.png'),
        # Electron packaged app: resources/psyclick_api/psyclick_api.exe + resources/images/*
        os.path.join(exe_dir, '..', 'images', 'LOGOggg.png'),
        # Also support running from resources root directly
        os.path.join(exe_dir, 'images', 'LOGOggg.png'),
        # frontend public (dev fallback)
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend', 'public', 'images', 'LOGOggg.png'),
    ]
    for p in candidates:
        if os.path.isfile(p):
            with open(p, 'rb') as f:
                return 'data:image/png;base64,' + base64.b64encode(f.read()).decode()
    return ''


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
    thr_str = f"{thr:.2f}" if thr != float("inf") else "N/A"
    logo_src = _logo_b64()

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
        colors = {1:"#3B82F6",2:"#0ABFBC",3:"#10B981",4:"#EF4444"}
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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Inter', 'Segoe UI', Arial, sans-serif; background: #F0F4F8; color: #1A2E35; }}
  .page {{ max-width: 920px; margin: 0 auto; padding: 36px 28px; }}

  /* ── Header bar ── */
  .header {{ background: white; border-radius: 16px; border: 1px solid #E4ECEC;
             box-shadow: 0 1px 4px rgba(10,191,188,.06);
             display:flex; justify-content:space-between; align-items:center;
             padding: 20px 26px; margin-bottom: 20px; }}
  .logo-wrap {{ display:flex; align-items:center; gap:12px; }}
  .logo-icon {{ width:40px; height:40px; background:linear-gradient(135deg,#0ABFBC,#08A8A5);
                border-radius:10px; display:flex; align-items:center; justify-content:center;
                font-size:22px; color:white; font-weight:900; line-height:1; }}
  .logo-text {{ font-size:20px; font-weight:800; color:#1A2E35; letter-spacing:-.3px; }}
  .logo-sub  {{ font-size:11px; color:#7A9A9A; font-weight:500; margin-top:1px; }}
  .meta {{ text-align:right; font-size:12px; color:#7A9A9A; line-height:1.7; }}
  .meta strong {{ color:#1A2E35; font-weight:600; }}
  .confidential {{ display:inline-block; background:#E0FAFA; color:#089F9D;
                   padding:3px 10px; border-radius:20px; font-size:10px;
                   font-weight:700; letter-spacing:.3px; margin-top:4px; }}

  /* ── Status banner ── */
  .banner {{ padding: 16px 20px; border-radius: 14px; margin-bottom: 18px;
             background: {fb}; border-left: 5px solid {fc};
             display:flex; align-items:center; gap:14px; }}
  .banner-dot {{ width:10px; height:10px; border-radius:50%; background:{fc}; flex-shrink:0; }}
  .banner h2 {{ color: {fc}; font-size: 15px; font-weight:700; margin-bottom: 2px; }}
  .banner p {{ color: #475569; font-size: 12px; line-height:1.5; }}

  /* ── Cards ── */
  .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 16px; }}
  .card {{ background: white; border: 1px solid #E4ECEC; border-radius: 14px;
           padding: 18px 20px; box-shadow: 0 1px 3px rgba(10,191,188,.04); }}
  .card h3 {{ font-size: 10px; color: #7A9A9A; font-weight: 700; margin-bottom: 8px;
              text-transform: uppercase; letter-spacing: .6px; }}
  .metric-val {{ font-size: 26px; font-weight: 800; letter-spacing:-.5px; }}
  .metric-sub {{ font-size: 11px; color: #7A9A9A; margin-top: 3px; }}
  .interp {{ font-size: 12px; color: #475569; margin-top: 10px; padding-top: 10px;
             border-top: 1px solid #F0F4F8; line-height: 1.55; }}

  /* ── Sections ── */
  .section {{ background: white; border: 1px solid #E4ECEC; border-radius: 14px;
              padding: 20px 22px; margin-bottom: 16px;
              box-shadow: 0 1px 3px rgba(10,191,188,.04); }}
  .section-title {{ font-size: 12px; font-weight: 700; color: #7A9A9A; text-transform:uppercase;
                    letter-spacing:.6px; margin-bottom: 14px; display:flex; align-items:center; gap:8px; }}
  .section-title::after {{ content:''; flex:1; height:1px; background:#F0F4F8; }}
  .section p {{ font-size: 13px; color: #475569; line-height: 1.6; }}

  /* ── Score bars ── */
  .score-bar-wrap {{ margin-bottom:12px; }}
  .score-label {{ display:flex; justify-content:space-between; font-size:12px; margin-bottom:5px; }}
  .score-label span {{ color:#7A9A9A; font-weight:500; }}
  .score-label strong {{ font-weight:700; }}
  .score-bar {{ background:#F0F4F8; border-radius:6px; height:8px; }}
  .score-fill {{ height:100%; border-radius:6px; }}

  /* ── Table ── */
  table {{ width:100%; border-collapse:collapse; font-size:11.5px; }}
  th {{ background:#F8FAFA; text-align:left; padding:9px 10px; color:#7A9A9A;
        font-weight:700; border-bottom:2px solid #E4ECEC; text-transform:uppercase;
        letter-spacing:.4px; font-size:10px; }}
  td {{ padding:9px 10px; border-bottom:1px solid #F0F4F8; vertical-align:middle; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background:#F8FAFA; }}

  /* ── Recs ── */
  .rec {{ display:flex; gap:14px; padding:12px 0; border-bottom:1px solid #F0F4F8; }}
  .rec:last-child {{ border-bottom:none; }}
  .rec-num {{ background:linear-gradient(135deg,#0ABFBC,#08A8A5); color:white; border-radius:50%;
              width:26px; height:26px; min-width:26px; display:flex; align-items:center;
              justify-content:center; font-weight:700; font-size:11px; margin-top:1px; }}
  .rec-title {{ font-weight:700; font-size:13px; color:#1A2E35; margin-bottom:4px; }}
  .rec-body  {{ font-size:12px; color:#475569; line-height:1.55; }}

  /* ── Footer ── */
  .footer {{ margin-top:24px; padding-top:14px; border-top:1px solid #E4ECEC;
             font-size:10px; color:#A0BABA; text-align:center; line-height:1.8; }}

  @media print {{
    body {{ background: white; }}
    .page {{ padding: 16px; }}
    .no-print {{ display: none !important; }}
    .card, .section {{ box-shadow: none; }}
  }}
</style>
</head>
<body>
<div class="page">

  <!-- HEADER -->
  <div class="header">
    <div class="logo-wrap">
      <div class="logo-icon">{'<img src="' + logo_src + '" style="width:28px;height:28px;object-fit:contain">' if logo_src else 'Ψ'}</div>
      <div>
        <div class="logo-text">PsyClick</div>
        <div class="logo-sub">Clinical Decision Support System</div>
      </div>
    </div>
    <div class="meta">
      <strong>Client ID:</strong> {pid}<br>
      <strong>Session Date:</strong> {ts[:16]}<br>
      <strong>Report Generated:</strong> {now}<br>
      <span class="confidential">CONFIDENTIAL — CLINICIAN USE ONLY</span>
    </div>
  </div>

  <!-- OVERALL STATUS BANNER -->
  <div class="banner">
    <div class="banner-dot"></div>
    <div>
      <h2>OVERALL STATUS: {flag} — {label}</h2>
      <p>{rat}</p>
    </div>
  </div>

  <!-- ROW 1: Screening + Fuzzy -->
  <div class="grid2">
    <div class="card">
      <h3>PHQ-9 / GAD-7 Screening</h3>
      <div class="score-bar-wrap">
        <div class="score-label">
          <span>PHQ-9 Depression</span>
          <strong style="color:#F27C7C">{phq}/27 — {_phq(phq)}</strong>
        </div>
        <div class="score-bar"><div class="score-fill" style="width:{min(phq/27*100,100):.0f}%;background:#F27C7C"></div></div>
      </div>
      <div class="score-bar-wrap">
        <div class="score-label">
          <span>GAD-7 Anxiety</span>
          <strong style="color:#F5A623">{gad}/21 — {_gad(gad)}</strong>
        </div>
        <div class="score-bar"><div class="score-fill" style="width:{min(gad/21*100,100):.0f}%;background:#F5A623"></div></div>
      </div>
    </div>
    <div class="card">
      <h3>Fuzzy Logic Classification</h3>
      <div style="font-size:22px;font-weight:800;color:{fc};letter-spacing:-.4px">{label}</div>
      <div style="font-size:12px;color:#7A9A9A;margin:4px 0 10px">Confidence: <strong style="color:#1A2E35">{int(conf*100)}%</strong></div>
      <div class="interp">The fuzzy classifier combines T², PSI, and PAI into a graded membership
      classification. Higher confidence means the pattern more clearly matches the labeled category.</div>
    </div>
  </div>

  <!-- ROW 2: 4 Metric cards -->
  <div class="grid2">
    <div class="card">
      <h3>T² Score (Hotelling's T²)</h3>
      <div class="metric-val" style="color:#F27C7C">{t2:.3f}</div>
      <div class="metric-sub">F-threshold (UCL): {thr_str}</div>
      <div class="interp">
        <strong>Interpretation:</strong> {_t2_interp(t2, thr)}<br><br>
        T² measures how far the client's behavioral fingerprint drifted from their own calibration
        baseline. A score above the threshold indicates a statistically significant psychomotor shift.
      </div>
    </div>
    <div class="card">
      <h3>PSI — Psychomotor Slowing Index</h3>
      <div class="metric-val" style="color:#5BA4CF">{psi:.3f}</div>
      <div class="metric-sub">Flight time · dwell time · pause frequency</div>
      <div class="interp">
        <strong>Interpretation:</strong> {_psi_interp(psi)}<br><br>
        PSI quantifies motor inhibition — slower keypresses, longer holds, and more frequent pauses.
        Mirrors the psychomotor retardation observable in depression.
      </div>
    </div>
    <div class="card">
      <h3>PAI — Psychomotor Agitation Index</h3>
      <div class="metric-val" style="color:#0ABFBC">{pai:.3f}</div>
      <div class="metric-sub">Jerk · path entropy · error rate · cursor velocity</div>
      <div class="interp">
        <strong>Interpretation:</strong> {_pai_interp(pai)}<br><br>
        PAI quantifies motor restlessness — cursor jerkiness and erratic movement paths corresponding
        to anxiety-driven hyperarousal patterns.
      </div>
    </div>
    <div class="card">
      <h3>Domain T² Profile</h3>
      {domain_svg if domain_svg else '<p style="color:#A0BABA;font-size:12px;margin-top:8px">No domain data available.</p>'}
      <div class="interp" style="margin-top:10px">Highest T² domain = strongest emotional vulnerability
      area for this session. Prioritize in the next therapeutic interview.</div>
    </div>
  </div>

  <!-- PER-QUESTION BIOMETRIC TABLE -->
  <div class="section">
    <div class="section-title">Per-Question Biometric Profile</div>
    <p style="margin-bottom:12px;font-size:12px;color:#7A9A9A">
      Flight time = avg inter-keystroke interval. Pause/s = cursor pause events per second.
      Hover words = words the cursor lingered on before typing. AMBER/RED items indicate
      that specific question triggered a significant psychomotor shift.
    </p>
    <table>
      <thead>
        <tr>
          <th>Item</th><th>Group</th><th>Lvl</th><th>T²</th><th>PSI</th><th>PAI</th>
          <th>Flight</th><th>Pause/s</th><th>Flag</th><th>Top Hover Words</th>
        </tr>
      </thead>
      <tbody>{snap_rows if snap_rows else '<tr><td colspan="10" style="text-align:center;color:#A0BABA;padding:20px">No per-question data available</td></tr>'}</tbody>
    </table>
  </div>

  <!-- CLINICAL RECOMMENDATIONS -->
  <div class="section">
    <div class="section-title">Clinical Recommendations</div>
    <p style="font-size:12px;color:#7A9A9A;margin-bottom:14px">
      Generated from the combined psychomotor profile, screening scores, and domain analysis.
      Intended to augment — not replace — clinical judgment.
    </p>
    <div id="recs"></div>
  </div>

  <div class="footer">
    <strong style="color:#1A2E35">PsyClick</strong> Clinical Decision Support System &nbsp;·&nbsp; Generated {now}<br>
    Decision support tool only. All clinical conclusions require professional interpretation by a licensed clinician.
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
                     "body": f"RED psychomotor flag combined with PHQ-9={phq} ({_phq(phq)}) and GAD-7={gad} ({_gad(gad)}) "
                             "warrants an immediate structured risk assessment. Do not defer to next session."})
    elif flag == "AMBER":
        recs.append({"title": "🟡 Prioritized Follow-Up Within 48–72 Hours",
                     "body": "Schedule a structured follow-up. Review flagged stressor domains before next session."})
    else:
        recs.append({"title": "🟢 Routine Monitoring",
                     "body": "Psychomotor indicators within normal range. Continue standard follow-up schedule."})

    if "Retardation" in label or (psi > pai and psi > 1.0):
        recs.append({"title": "🧠 Psychomotor Slowing Pattern (PSI)",
                     "body": f"PSI={psi:.3f}. Client shows reduced motor speed, extended key intervals, and frequent pauses. "
                             "Explore topics related to energy, motivation, and processing speed in the clinical interview."})
    elif "Agitation" in label or (pai > psi and pai > 1.0):
        recs.append({"title": "⚡ Psychomotor Restlessness Pattern (PAI)",
                     "body": f"PAI={pai:.3f}. Client exhibits erratic cursor movement, typing irregularities, and high keystroke variability. "
                             "Dive into specific stressors, triggers, and environmental factors in the discussion."})
    elif "Mixed" in label and psi > 0.5 and pai > 0.5:
        recs.append({"title": "🔀 Mixed Psychomotor Pattern",
                     "body": f"Both PSI={psi:.3f} and PAI={pai:.3f} elevated. Client demonstrates both slowing and restlessness. "
                             "Explore the timeline and context of when each pattern emerges during the assessment."})

    if phq >= 20:
        recs.append({"title": f"📋 PHQ-9 Score: {phq}/27 (Severe)",
                     "body": f"Clinically significant elevation. Client endorsed multiple depressive symptoms across the assessment period. "
                             "Explore patterns and specific symptom clusters in follow-up discussion."})
    elif phq >= 15:
        recs.append({"title": f"📋 PHQ-9 Score: {phq}/27 (Moderately Severe)",
                     "body": f"Notable elevation indicating significant symptom burden. "
                             "Discuss specific symptoms and their impact on daily function in next session."})

    if gad >= 15:
        recs.append({"title": f"📋 GAD-7 Score: {gad}/21 (Severe)",
                     "body": f"Clinically significant anxiety symptoms across multiple domains. "
                             "Explore specific worry topics and their temporal patterns in the clinical interview."})
    elif gad >= 10:
        recs.append({"title": f"📋 GAD-7 Score: {gad}/21 (Moderate-to-Severe)",
                     "body": f"Notable anxiety elevation. "
                             "Discuss specific triggers and contexts where anxiety is most prominent."})

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
    """Save individual HTML report and open in browser. Returns filepath."""
    html = generate_html_report(data)
    if not filepath:
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        pid  = data.get("student_id", "unknown")
        name = f"PsyClick_Report_{pid}_{ts}.html"
        filepath = os.path.join(os.path.expanduser("~"), "Desktop", name)
        
        if not os.path.isdir(os.path.dirname(filepath)):
            filepath = os.path.join(tempfile.gettempdir(), name)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    return filepath

  
# ─── PHQ / GAD label helpers (mirrors app.py, kept local so exporter is standalone) ───
def _phq_label(s):
    if s <= 4:  return "Minimal"
    if s <= 9:  return "Mild"
    if s <= 14: return "Moderate"
    if s <= 19: return "Mod-Severe"
    return "Severe"

def _gad_label(s):
    if s <= 4:  return "Minimal"
    if s <= 9:  return "Mild"
    if s <= 14: return "Moderate"
    return "Severe"


def generate_summary_html(rows):
    """
    Build a professional HTML summary report for all sessions.
    rows: list of (student_id, timestamp, flag, phq, gad, psi, pai, label)
    """
    now      = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    logo_src = _logo_b64()
    total = len(rows)
    red   = sum(1 for r in rows if r[2] == "RED")
    amber = sum(1 for r in rows if r[2] == "AMBER")
    green = sum(1 for r in rows if r[2] == "GREEN")

    # Build table rows
    tbody = ""
    for pid, ts, flag, phq, gad, psi, pai, label in rows:
        fc  = _flag_color(flag or "GREEN")
        fb  = _flag_bg(flag or "GREEN")
        phq = phq or 0
        gad = gad or 0
        psi = psi or 0.0
        pai = pai or 0.0
        tbody += f"""
        <tr>
          <td><strong style="color:#1E293B">{pid}</strong></td>
          <td style="color:#64748B;font-size:11px">{ts}</td>
          <td><span style="background:{fb};color:{fc};padding:3px 10px;border-radius:10px;
                           font-size:11px;font-weight:700">{flag or 'GREEN'}</span></td>
          <td>{phq} <span style="color:#94A3B8;font-size:10px">({_phq_label(phq)})</span></td>
          <td>{gad} <span style="color:#94A3B8;font-size:10px">({_gad_label(gad)})</span></td>
          <td style="color:#3B82F6;font-weight:600">{psi:.3f}</td>
          <td style="color:#0ABFBC;font-weight:600">{pai:.3f}</td>
          <td style="font-size:12px;color:#475569">{label or 'Normal'}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>PsyClick — Session Summary Report</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Inter', 'Segoe UI', Arial, sans-serif; background: #F0F4F8; color: #1A2E35; }}
  .page {{ max-width: 1020px; margin: 0 auto; padding: 36px 28px; }}
  .header {{ background:white; border-radius:16px; border:1px solid #E4ECEC;
             box-shadow:0 1px 4px rgba(10,191,188,.06);
             display:flex; justify-content:space-between; align-items:center;
             padding:20px 26px; margin-bottom:20px; }}
  .logo-wrap {{ display:flex; align-items:center; gap:12px; }}
  .logo-icon {{ width:40px; height:40px; background:linear-gradient(135deg,#0ABFBC,#08A8A5);
                border-radius:10px; display:flex; align-items:center; justify-content:center;
                font-size:22px; color:white; font-weight:900; line-height:1; }}
  .logo-text {{ font-size:20px; font-weight:800; color:#1A2E35; letter-spacing:-.3px; }}
  .logo-sub  {{ font-size:11px; color:#7A9A9A; font-weight:500; margin-top:1px; }}
  .meta {{ text-align:right; font-size:12px; color:#7A9A9A; line-height:1.7; }}
  .meta strong {{ color:#1A2E35; font-weight:600; }}
  .confidential {{ display:inline-block; background:#E0FAFA; color:#089F9D;
                   padding:3px 10px; border-radius:20px; font-size:10px;
                   font-weight:700; letter-spacing:.3px; margin-top:4px; }}
  .stats {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:18px; }}
  .stat {{ background:white; border:1px solid #E4ECEC; border-radius:14px;
           padding:18px 20px; text-align:center;
           box-shadow:0 1px 3px rgba(10,191,188,.04); }}
  .stat-val {{ font-size:30px; font-weight:800; letter-spacing:-.5px; }}
  .stat-lbl {{ font-size:11px; color:#7A9A9A; margin-top:4px; font-weight:500; }}
  .section {{ background:white; border:1px solid #E4ECEC; border-radius:14px;
              padding:20px 22px; margin-bottom:16px;
              box-shadow:0 1px 3px rgba(10,191,188,.04); }}
  .section-title {{ font-size:10px; font-weight:700; color:#7A9A9A; text-transform:uppercase;
                    letter-spacing:.6px; margin-bottom:14px; display:flex; align-items:center; gap:8px; }}
  .section-title::after {{ content:''; flex:1; height:1px; background:#F0F4F8; }}
  table {{ width:100%; border-collapse:collapse; font-size:12px; }}
  th {{ background:#F8FAFA; text-align:left; padding:9px 12px; color:#7A9A9A;
        font-weight:700; border-bottom:2px solid #E4ECEC; font-size:10px;
        text-transform:uppercase; letter-spacing:.5px; }}
  td {{ padding:10px 12px; border-bottom:1px solid #F0F4F8; vertical-align:middle; }}
  tr:last-child td {{ border-bottom:none; }}
  tr:hover td {{ background:#F8FAFA; }}
  .footer {{ margin-top:24px; padding-top:14px; border-top:1px solid #E4ECEC;
             font-size:10px; color:#A0BABA; text-align:center; line-height:1.8; }}
  @media print {{
    body {{ background: white; }}
    .page {{ padding: 16px; }}
    .stat, .section {{ box-shadow: none; }}
  }}
</style>
</head>
<body>
<div class="page">
  <div class="header">
    <div class="logo-wrap">
      <div class="logo-icon">{'<img src="' + logo_src + '" style="width:28px;height:28px;object-fit:contain">' if logo_src else 'Ψ'}</div>
      <div>
        <div class="logo-text">PsyClick</div>
        <div class="logo-sub">Session Summary Report</div>
      </div>
    </div>
    <div class="meta">
      <strong>Generated:</strong> {now}<br>
      <strong>Total Sessions:</strong> {total}<br>
      <span class="confidential">CONFIDENTIAL — CLINICIAN USE ONLY</span>
    </div>
  </div>

  <div class="stats">
    <div class="stat">
      <div class="stat-val" style="color:#1A2E35">{total}</div>
      <div class="stat-lbl">Total Sessions</div>
    </div>
    <div class="stat">
      <div class="stat-val" style="color:#F27C7C">{red}</div>
      <div class="stat-lbl">RED — High Risk</div>
    </div>
    <div class="stat">
      <div class="stat-val" style="color:#F5A623">{amber}</div>
      <div class="stat-lbl">AMBER — Monitor</div>
    </div>
    <div class="stat">
      <div class="stat-val" style="color:#36C98E">{green}</div>
      <div class="stat-lbl">GREEN — Normal</div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">All Sessions</div>
    <table>
      <thead>
        <tr>
          <th>Client ID</th><th>Date &amp; Time</th><th>Status</th>
          <th>PHQ-9</th><th>GAD-7</th><th>PSI</th><th>PAI</th><th>Classification</th>
        </tr>
      </thead>
      <tbody>{tbody if tbody else
        '<tr><td colspan="8" style="text-align:center;color:#A0BABA;padding:20px">No sessions recorded</td></tr>'
      }</tbody>
    </table>
  </div>

  <div class="footer">
    <strong style="color:#1A2E35">PsyClick</strong> Clinical Decision Support System &nbsp;·&nbsp; Generated {now}<br>
    Decision support tool only. All clinical conclusions require professional interpretation by a licensed clinician.
  </div>
</div>
</body>
</html>"""
    return html


def export_summary(rows, filepath=None):
    """Save summary HTML report and open in browser. Returns filepath."""
    html = generate_summary_html(rows)
    if not filepath:
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"PsyClick_Summary_{ts}.html"
        filepath = os.path.join(os.path.expanduser("~"), "Desktop", name)
        if not os.path.isdir(os.path.dirname(filepath)):
            filepath = os.path.join(tempfile.gettempdir(), name)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return filepath
