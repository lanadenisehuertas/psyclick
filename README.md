# PsyClick User Guide

PsyClick is a Windows desktop app for clinician-guided psychomotor and screening sessions. It supports two main workflows:

- Clinician workflow: register or sign in, run client sessions, review results, export reports, and manage records.
- Normative tester workflow: complete baseline testing sessions that contribute to the normative reference dataset.

This guide is written for non-developers. Follow only the section for your role unless your supervisor asks you to do otherwise.

---

## 1. Before You Start

You need:

- A Windows computer.
- Internet access.
- The PsyClick installer or portable app.
- A working mouse and keyboard.
- Permission from your clinic/research team to use the app.

If your organization uses the cloud database, PsyClick must be connected to Supabase. The app package should already include the correct database connection. If it does not connect, contact the administrator before collecting sessions.

---

## 2. Installation and Setup

### Install the app

1. Open the PsyClick installer, usually named `PsyClick Setup.exe`.
2. If Windows SmartScreen appears, choose `More info`, then `Run anyway`.
3. Complete the installer.
4. Open PsyClick from the Start Menu or desktop shortcut.

### Database setup

For normal distributed use, the app should already contain the correct database configuration.

If an administrator asks you to install the database configuration manually:

1. Press `Win + R`.
2. Type `%APPDATA%` and press Enter.
3. Open or create the folder named `PsyClick`.
4. Place `config.json` inside this folder.
5. Restart PsyClick.

Expected path:

```text
%APPDATA%\PsyClick\config.json
```

If Supabase is unavailable, PsyClick shows a database connection error. It should not continue with hidden local-only data when Supabase is configured.

---

## 3. Clinician Instructions

Use this section if you are a clinician or staff member running client sessions.

### Clinician account creation

Use this only the first time you create your clinician account.

1. Open PsyClick.
2. On the login page, choose `Don't have an account? Register`.
3. Enter your full name.
4. Enter a password.
5. Click `Register`.
6. PsyClick will generate your Clinician ID.
7. Save your Clinician ID securely. You will need it for future logins.

Clinician ID format:

```text
YYYYNNN
```

Example:

```text
2026001
```

### Clinician login

1. Open PsyClick.
2. Enter your Clinician ID.
3. Enter your password.
4. Click `Sign In`.

If login fails:

- Make sure the Clinician ID is numbers only.
- Check Caps Lock.
- Confirm you are using the same database/environment where the account was created.
- If you see a Supabase or database error, stop and contact the administrator.

### Dashboard

After signing in, the dashboard shows:

- Total clients.
- Sessions this week.
- No Concerns count.
- Need Review count.
- Session overview chart.
- Sessions this week chart.
- Recent session list.

Main dashboard actions:

- `New Intake`: starts a new client session.
- Search clients: filters recent sessions by client ID.
- Filter button: filters recent sessions by status.
- `Export`: exports a summary report.
- `View All`: opens the full client database.
- Clicking any recent session opens its report.

### Starting a new client intake

1. Click `New Intake`.
2. Enter the client's full name or client ID.
3. Ask the client to review the consent statement.
4. Tick the consent checkbox.
5. Click `Agree & Begin Baseline Calibration`.
6. Enter your clinician password if prompted.

Important:

- The Client ID is the identifier used in the database.
- Client IDs should start at `C-001` and continue upward, for example `C-001`, `C-002`, `C-003`.
- If the client already has previous sessions, PsyClick asks whether to start a new session. Existing data is preserved.
- Do not start a session without consent.

### Required session order

Run the session in this order:

1. Keyboard calibration.
2. Mouse calibration.
3. PHQ-9.
4. GAD-7.
5. Emotional response task.
6. Final report.

Do not skip steps unless your protocol specifically allows it.

### Keyboard calibration

The client sees a `Typing Task`.

Instructions for the client:

1. Type the displayed paragraph exactly as shown.
2. Type naturally at a normal pace.
3. Do not rush.
4. Click `Continue` when finished.

The app records typing rhythm and baseline keyboard features.

### Mouse calibration

The client sees a `Click Task`.

Instructions for the client:

1. Click each numbered circle in order.
2. Move naturally at a normal pace.
3. Finish all 5 circles.
4. Click `Continue`.

The app records mouse movement and click behavior.

### PHQ-9 screening

The client answers 9 questions about the last 2 weeks.

Options:

- `0` Not at all
- `1` Several days
- `2` More than half days
- `3` Nearly every day

The client must answer all questions before continuing.

### GAD-7 screening

The client answers 7 questions about the last 2 weeks.

Options:

- `0` Not at all
- `1` Several days
- `2` More than half days
- `3` Nearly every day

The client must answer all questions before continuing.

### Emotional response task

The client answers 12 written prompts.

Instructions for the client:

1. Read each prompt carefully.
2. Type a response in their own words.
3. Respond naturally.
4. Avoid switching windows or using other apps.
5. Continue until all 12 prompts are complete.

The response box has a 500-character limit per prompt.

At the end, clinicians may be asked to confirm with their password before the final report is generated.

### Final report

The final report includes:

- Overall risk flag.
- PHQ-9 score.
- GAD-7 score.
- Hotelling T2 score.
- Psychomotor Stress Index (PSI).
- Psychomotor Anxiety Index (PAI).
- Temporal hesitation heatmap.
- Keystroke flight time distribution.
- Domain T2 scores.
- Emotional load level scores.
- Normative comparison when available.
- Clinical recommendation text.
- Per-question biomarker table.

Actions:

- `Back`: returns to dashboard or client detail.
- `Export Full Report`: exports the current report file.

### Client database

Open `Clients` from the sidebar.

You can:

- Search by client ID.
- Filter by `All Clients`, `No Concerns`, or `Need Review`.
- Open a client record.
- View total sessions, last seen date, and latest status.

### Client detail page

The client detail page shows:

- Latest status.
- Latest PHQ-9 and GAD-7 scores.
- Latest PSI, PAI, and T2 values.
- Full session history.

Actions:

- `Back to Client Database`: returns to the client list.
- `View Report`: opens a specific session report.
- `Delete Record`: permanently deletes the client and all sessions. Use this carefully.

### Audit log

Open `Audit` from the sidebar.

Tabs:

- `Clinician Activity`: login, logout, export, intake actions.
- `Client Activity`: session progress and client task events.

Use this page for compliance review and troubleshooting.

### Normative dashboard for clinicians

Open `Normative` from the sidebar.

Clinicians can:

- See how many normative sessions have been collected.
- Start a normative session for a tester.
- Compute or recompute the normative baseline.

To compute the baseline:

1. Open `Normative`.
2. Click `Compute Baseline` or `Recompute`.
3. Enter your clinician password.
4. Click `Confirm`.

The baseline can be computed from available normative sessions. The target shown in the interface is 100 sessions.

---

## 4. Normative Tester Instructions

Use this section if you are a tester contributing to the normative baseline.

### Tester purpose

Normative tester sessions are used to build a reference dataset for comparison. These sessions are not regular clinical client sessions.

### Tester login

1. Open PsyClick.
2. Click `Normative Tester Portal` on the clinician login screen.
3. Enter your assigned Tester ID.
4. Enter the session password.
5. Click `Begin Normative Session`.

Tester ID:

- Use the ID assigned by the research or clinic team.
- Tester IDs should start at `T-001` and continue upward, for example `T-001`, `T-002`, `T-003`.

Tester password:

```text
NORMER123
```

Keep this password restricted to authorized testers only.

### Tester session flow

Complete the full flow:

1. Keyboard calibration.
2. Mouse calibration.
3. PHQ-9.
4. GAD-7.
5. Emotional response task.
6. Session complete page.

### Tester rules

Before starting:

- Use a stable internet connection.
- Use the same keyboard and mouse for the whole session.
- Sit comfortably.
- Close unnecessary apps.

During the session:

- Type naturally.
- Move the mouse naturally.
- Do not rush.
- Do not intentionally perform poorly.
- Do not switch windows repeatedly.
- Do not use a phone during active tasks.
- Ask the supervisor if you do not understand a prompt.

After completion:

- The app shows `Session Complete`.
- Click `Exit Portal`.
- Tell the supervisor that the session is done.

---

## 5. What the Client or Tester Should Be Told

You may read this aloud:

> You will complete a few typing, mouse, and questionnaire tasks. Please answer honestly and type naturally. The system records typing and mouse interaction patterns during the task. There are no right or wrong answers. If you are unsure what to do, ask before continuing.

For clinical clients, also confirm that consent has been given according to your clinic's procedure.

---

## 6. Status Flags and Scores

PsyClick may show these flags:

- `GREEN`: no immediate psychomotor concern detected by the system.
- `AMBER`: moderate concerns or review recommended.
- `RED`: significant concerns or review recommended.

Screening score ranges shown in the app:

PHQ-9:

- 0-4: Minimal
- 5-9: Mild
- 10-14: Moderate
- 15-19: Moderately severe
- 20-27: Severe

GAD-7:

- 0-4: Minimal
- 5-9: Mild
- 10-14: Moderate
- 15-21: Severe

PsyClick is a decision support tool. It does not replace clinical judgment, diagnosis, risk assessment, or emergency procedures.

---

## 7. Exports

Available exports:

- Dashboard `Export`: exports a session summary.
- Report `Export Full Report`: exports a detailed individual report.

If export fails:

- Confirm at least one completed session exists.
- Reopen the report and try again.
- Check that Windows allows the app to write files.
- Contact the administrator if the error continues.

---

## 8. Troubleshooting

### The app keeps loading during sign in

Possible causes:

- Supabase is unreachable.
- The database password is wrong.
- The packaged config is missing or stale.
- The user's internet is blocked by firewall or network policy.

What to do:

1. Restart the app.
2. Confirm internet access.
3. Contact the administrator with the exact error text.

### Clinician cannot sign in

Check:

- Clinician ID is numeric.
- Password is correct.
- The account exists in the current Supabase database.
- Caps Lock is off.

### Tester cannot sign in

Check:

- Tester ID is entered.
- Password is exactly `NORMER123`.
- The tester is using the Normative Tester Portal, not clinician login.

### Data does not appear in Supabase

Check:

- Internet connection.
- App was rebuilt with the latest `config.json`.
- `%APPDATA%\PsyClick\config.json` is correct if manually configured.
- You are viewing the correct Supabase project.
- The session reached the final completion/report step.

### A client already exists

If PsyClick says the client already has sessions, choose whether to start a new session. Existing sessions are preserved unless you use `Delete Record`.

### Delete record warning

`Delete Record` removes the client and all sessions for that client. This cannot be undone from the app.

---

## 9. Security Notes

- Do not share clinician passwords in plain text.
- Store Clinician IDs and passwords securely.
- Share the normative tester password only with authorized testers.
- Do not publish `config.json` publicly.
- If a password or database URL is exposed, rotate it immediately in Supabase and rebuild the app.

---

## 10. Support Checklist

When reporting a problem, include:

- Role: clinician or tester.
- App version.
- Exact screen where the issue happened.
- Exact error message.
- Clinician ID or Tester ID, but never the password.
- Whether internet was working.
- Whether the issue happens on one machine or all machines.
- Whether the session reached the final report or complete page.
