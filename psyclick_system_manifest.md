# PsyClick Master System Manifest: Context & Architecture Guide

This document is the **Comprehensive System Manifest** for PsyClick. You can feed this document into any Large Language Model (LLM) or AI assistant to instantly grant them 100% accurate, code-aligned context about the system's architecture, formulas, logic, and clinical methodology.

---

## 1. System Overview & Core Concept
**PsyClick** is a "White-Box" Clinical Decision Support System (CDSS) designed to detect single-session psychomotor disturbances. It captures millisecond-level keystroke and cursor telemetry during a patient's clinical intake session to provide a licensed clinical psychologist with an objective "heatmap" of psychological stressors, directing them to the specific topics they should explore during the interview.

*   **Clinical Deployment**: Used by a clinical psychologist as a pre-session screening tool.
*   **Methodology**: Bridges ipsative (within-session, self-referential) tracking with normative (population-level) benchmarking.

## 2. Technical Stack & Architecture
*   **Frontend**: React 18 + Vite 5 + JavaScript/JSX (Patient Assessment View & Clinician Dashboard).
*   **Desktop Shell**: Electron 29 (allows low-level OS access).
*   **Backend Application Logic**: Python (using `pynput` for background event listening, `numpy` & `scipy` for statistical computations).
*   **Database (`database_manager.py`)**: Dual-mode architecture. 
    *   *Cloud*: Supabase PostgreSQL (primary, with role-based access).
    *   *Local*: SQLite (robust offline fallback for environments without connectivity).
*   **Privacy Architecture**: "Local-First". The real-time behavioral baseline (mean vector and covariance matrix) is strictly held in session memory (O(1) memory footprint: <600 bytes) and securely discarded upon session termination.

---

## 3. The 8-Stage Detection Pipeline

### Stage 0: Hardware Abstraction Layer (HAL)
*   **Location**: `dynamics_logger.py`
*   **Purpose**: Neutralizes hardware polling noise and quantization artifacts from raw OS timestamps so that downstream data strictly reflects human behavior.
*   **Algorithm**: Grid-alignment Jitter Compensation (adapted from Cervin et al., 2004).
*   **Formula**: $t_{norm} = t_{raw} - (t_{raw} \bmod 0.001) + \delta_{latency} + debounce$
*   **Specifics**: 
    *   Target polling grid ($P_{target}$) = 1 ms (0.001s).
    *   For mechanical keyboards, a hardcoded `_DEBOUNCE = -0.0023` ($-2.3$ ms) is applied to compensate for early switch actuation.

### Stage 1: Sliding Window Filter
*   **Location**: `feature_extractor.py`
*   **Purpose**: Attenuates high-frequency hardware noise (>8 Hz, e.g., vibrations) from cursor coordinates while preserving clinically relevant hesitation patterns (<2 Hz).
*   **Algorithm**: 5-sample Gaussian-approximate weighted moving average.
*   **Kernel Weights**: $w = [0.1, 0.2, 0.4, 0.2, 0.1]$

### Stage 2: Within-Session EWMA Baseline Construction
*   **Location**: `anomaly_engine.py` (via `EWMABaseline` class)
*   **Purpose**: Dynamically constructs an individualized baseline during a 2-minute neutral calibration task to account for early-session nervousness.
*   **Algorithm**: Exponentially Weighted Moving Average (EWMA) applied to both the mean vector ($\mu$) and covariance matrix ($S$).
*   **Formula**: 
    *   $\mu_{ewma,t} = \lambda \cdot x_t + (1 - \lambda) \cdot \mu_{ewma,t-1}$
    *   $S_{ewma,t} = \lambda \cdot (x_t - \mu_t)(x_t - \mu_t)^T + (1 - \lambda) \cdot S_{ewma,t-1}$
*   **Specifics**: Smoothing parameter $\lambda = 0.2$. Code temporarily masks missing features with the EWMA mean to prevent precision matrix destabilization.

### Stage 3: Feature Extraction (8 Biomarkers)
*   **Location**: `feature_extractor.py`
*   **Biomarkers**:
    1.  **Flight Time**: Mean latency between consecutive key presses (s).
    2.  **Dwell Time**: Mean key-hold duration (s).
    3.  **Typing Velocity**: Keystrokes per second.
    4.  **Error Rate**: Proportion of backspace events.
    5.  **Cursor Velocity**: Mean tangential velocity (px/s).
    6.  **Jerk**: 3rd derivative of position (absolute mean of acceleration diffs, px/s³).
    7.  **Path Entropy**: Shannon entropy of discretized trajectory angles.
    8.  **Pause Frequency**: Count of movement cessations > 500 ms per second.
*   **Crucial Payload**: The module also extracts `pause_coords` (raw $x/y$ clusters of hesitations) to generate real-time spatial heatmaps.

### Stage 4: Multivariate Anomaly Detection
*   **Location**: `anomaly_engine.py` (`compute_t2()`)
*   **Purpose**: Evaluates all 8 biomarkers simultaneously.
*   **Algorithm**: Hotelling's T² with Ledoit-Wolf Ridge Shrinkage.
*   **Formulas**:
    *   T² Statistic: $T^2 = n(x - \mu_{ewma})^T S^{-1} (x - \mu_{ewma})$
    *   Ledoit-Wolf Shrinkage (Correlation space): $R_{reg} = (1 - \alpha) \cdot R_{emp} + \alpha \cdot I_p$
*   **Specifics**:
    *   Shrinkage ($\alpha$) = $0.15$ for small samples ($n < 40$), relaxing to $0.05$ for $n \ge 40$.
    *   Threshold evaluates against an F-distribution limit ($\alpha=0.05$). Falls back to Chi-Square critical value ($\chi^2 = 15.51$) when $n \le 8$.

### Stage 5: Feature Contribution Analysis
*   **Location**: `anomaly_engine.py` (`compute_contributions()`)
*   **Purpose**: Decomposes the T² scalar into directional psychomotor profiles using the Mason & Young (2002) formula.
*   **Indices**:
    *   **Psychomotor Slowing Index (PSI)**: Aggregates elevated Flight Time, Dwell Time, and Pause Frequency. Indicates motor inhibition/retardation.
    *   **Psychomotor Agitation Index (PAI)**: Aggregates Path Entropy, Jerk, Error Rate, Cursor Velocity, and depressed Typing Velocity. Indicates motor restlessness/anxiety.

### Stage 6 & 7: Fuzzy Logic Classifier & Heuristic Decision Tree
*   **Location**: `anomaly_engine.py` (`fuzzy_classify()`)
*   **Fuzzification**: Converts T², PSI, and PAI into 3 linguistic categories (Low, Moderate, High) using custom `_trimf` and `_trapmf` functions.
*   **Rule Base (Mamdani Min-Conjunction)**:
    1.  T² High AND PSI High AND PAI High $\rightarrow$ Mixed Disturbance, Severe (Highest Priority)
    2.  T² High AND PSI High AND PAI Low $\rightarrow$ Psychomotor Retardation, Severe
    3.  T² High AND PAI High AND PSI Low $\rightarrow$ Psychomotor Agitation, Severe
    4.  T² Mod AND PSI Mod AND PAI Mod $\rightarrow$ Mixed Disturbance, Borderline
    5.  T² Mod AND PAI Mod $\rightarrow$ Psychomotor Agitation, Borderline
    6.  T² Mod AND PSI Mod $\rightarrow$ Psychomotor Retardation, Borderline
    7.  T² Low $\rightarrow$ Normal
*   **Defuzzification**: Uses dominant-rule confidence scoring.
*   **Heuristic Thresholding (Clinical Flags)**:
    *   🟢 **Green**: T² ratio $\le 1.0$.
    *   🟡 **Amber**: $1.0 <$ T² ratio $\le 1.5$, or Borderline rules dominate.
    *   🔴 **Red**: T² ratio $> 1.5$ AND Severe rules dominate.

---

## 4. Empirical Data & Clinical Methodology

### The 100-Person Normative Baseline
*   **Methodology**: 100 adult participants were screened using a clinical-psychologist-validated Google Form to verify stable mental wellbeing. 
*   **Data Usage**: These healthy individuals took the PsyClick test. Their resulting keystroke/cursor metrics were processed and stored in the `normative_stats` database table using Bessel's correction ($n-1$) to establish a rigorous, unbiased population variance standard.

### Clinical Utility Integration
*   The system was adopted by the clinical psychologist as a pre-session screener. 
*   **Domain-Segmented Profiling**: Microstressor prompts are tagged by domain (Time/Workload, Interpersonal, Academic/Performance, Self-Evaluation).
*   **The Heatmap**: Clinicians use the `pause_coords` heatmap to visually trace exactly which emotionally loaded words on the screen caused the patient's cursor to hesitate.
*   **Outcome**: The psychologist uses these objective red/amber flags and spatial heatmaps to bypass generic questions and immediately address high-stress topics during the clinical interview.

### ISO/IEC 25010 Software Quality Evaluation
*   Evaluated by IT domain experts across 5 characteristics: Functional Suitability, Performance Efficiency (hybrid module-based architecture, O(N) complexity), Usability (white-box reporting), Reliability (Supabase/SQLite failover), and Security (Local-first, in-memory processing).
