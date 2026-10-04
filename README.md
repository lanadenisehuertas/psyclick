<div align="center">
  <a href="https://psyclick-app.vercel.app/">
    <img src="./images/LOGO%20WITH%20WORD.png" alt="PsyClick" width="520" />
  </a>

  <p><strong>A calmer, clinician-guided approach to psychomotor screening.</strong></p>
  <p>
    PsyClick combines validated questionnaires with typing rhythm, mouse dynamics,
    and emotional-response tasks to create clear decision-support reports for clinical review.
  </p>

  <p>
    <a href="https://psyclick-app.vercel.app/"><strong>Explore the website</strong></a>
    ·
    <a href="https://psyclick-app.vercel.app/#download">Download PsyClick</a>
    ·
    <a href="#getting-started">Run locally</a>
  </p>

  <p>
    <img alt="Platform: Windows" src="https://img.shields.io/badge/Platform-Windows-70D6C5?style=flat-square&logo=windows11&logoColor=0B172A" />
    <img alt="Frontend: React and Electron" src="https://img.shields.io/badge/Desktop-React%20%2B%20Electron-7EDFE7?style=flat-square&logo=electron&logoColor=0B172A" />
    <img alt="Backend: Python and Flask" src="https://img.shields.io/badge/API-Python%20%2B%20Flask-A8E6CF?style=flat-square&logo=python&logoColor=0B172A" />
    <img alt="Clinical decision support" src="https://img.shields.io/badge/Purpose-Decision%20Support-B7F3D0?style=flat-square" />
  </p>
</div>

---

## One assessment, a clearer clinical picture

PsyClick is a desktop clinical decision-support system that turns a guided screening session into an interpretable report. It helps clinicians see behavioral changes alongside familiar questionnaire scores without treating any single signal as a diagnosis.

| Guided experience | Interpretable results |
| --- | --- |
| **Validated screening** with PHQ-9 and GAD-7 questionnaires | **Traffic-light flags** make review priority easy to scan |
| **Behavioral signals** from keystroke timing and cursor movement | **PSI and PAI profiles** surface slowing and agitation patterns |
| **Emotional-response tasks** organized around relevant stress domains | **Session heatmaps** show where hesitation appeared during a task |
| **Local-first collection** with an offline SQLite fallback | **Clinician reports** combine questionnaire and behavioral context |

## How it works

```text
Guided intake
     ↓
Typing + cursor telemetry
     ↓
Feature extraction and within-session EWMA baseline
     ↓
Hotelling T² + PSI/PAI contribution analysis
     ↓
GREEN / AMBER / RED decision-support report
     ↓
Clinician review
```

The analysis pipeline evaluates eight behavioral features, including flight time, dwell time, typing velocity, error rate, cursor velocity, jerk, path entropy, and pause frequency. The implementation and methodology are documented in [`psyclick_system_manifest.md`](./psyclick_system_manifest.md).

## Built for focused, responsible screening

- **Calm by design** — the mint, aqua, and white interface keeps dense clinical information approachable.
- **Transparent analysis** — reports expose questionnaire scores, anomaly measures, and feature contributions instead of a black-box conclusion.
- **Resilient storage** — the clinical build supports local SQLite operation, with cloud-backed workflows available where configured.
- **Role-aware workflows** — separate patient assessment and clinician review experiences keep each task focused.
- **Offline capable** — the Windows desktop application can operate without a persistent internet connection.

> [!IMPORTANT]
> PsyClick is a screening and clinical decision-support tool. It does not diagnose a condition and must not replace evaluation by a qualified mental-health professional.

## Technology

| Layer | Stack |
| --- | --- |
| Desktop experience | Electron, React 18, Vite, Tailwind CSS |
| Local API | Python, Flask |
| Behavioral analysis | NumPy, SciPy, pandas |
| Storage | SQLite offline fallback, Supabase when configured |
| Reporting | Recharts and clinician-facing exports |

## Getting started

### Requirements

- Windows 10 or 11
- Python 3.13+
- Node.js 20+ and npm

### Clinical edition

```powershell
git clone https://github.com/lanadenisehuertas/psyclick.git
cd psyclick\psyclick-clinical

python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt

cd frontend
npm install
npm run build
cd ..

python api_server.py
```

For desktop development, open a second terminal in `psyclick-clinical/frontend` and run:

```powershell
npm run electron:dev
```

The hardened experimental variant and its security regression tests live in [`psyclick-secure`](./psyclick-secure/README.md).

## Repository map

```text
psyclick/
├── psyclick-clinical/      # Current clinical desktop application and API
│   ├── frontend/           # React, Vite, and Electron interface
│   └── tests/              # Clinical and security-focused tests
├── psyclick-secure/        # Hardened experimental build
├── images/                 # Product branding used by the applications
└── psyclick_system_manifest.md
```

Generated installers, virtual environments, office documents, database files, and build output are intentionally excluded from source control. Release downloads are available through the [PsyClick website](https://psyclick-app.vercel.app/#download).

## Team ByteMe

| Member | Role |
| --- | --- |
| **Jon Añonuevo** | System Architect & Lead Backend Developer |
| **Denise Ballano** | Full-Stack Developer & QA |
| **Lana Huertas** | Project Manager, Backend Developer & Lead UI/UX Designer |
| **Judea Tablate** | Lead Researcher & Documentation |

<div align="center">
  <sub>Designed to support thoughtful conversations—not replace them.</sub>
</div>
