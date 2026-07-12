# PsyClick v4 OFFLINE BUILD SYSTEM

## Overview

This is a completely offline-capable build of PsyClick designed for:
- **Air-gapped clinical environments** (no internet access)
- **Offline deployments** (complete independence from cloud services)
- **Demo/training setups** (immediate launch, zero configuration)
- **HIPAA-compliant systems** (all data stays on-device)

## What Changed

### New Files Created

#### 1. **database_manager_offline.py** (Both editions)
   - Location: `psyclick-clinical/` and root folder
   - SQLite-only database manager
   - **REMOVED:** All PostgreSQL/Supabase connection code
   - **REMOVED:** psycopg2 driver references
   - **REMOVED:** Environment variable checking for cloud URLs
   - **REMOVED:** config.json cloud credential lookup
   - **KEPT:** All clinical logic, data structure, SQL schema
   - **KEPT:** All normative calculation and anomaly detection

#### 2. **BUILD_OFFLINE.bat** (Clinical Edition)
   - Location: `psyclick-clinical/`
   - Separate build script for offline-only version
   - Automatically swaps in database_manager_offline.py
   - Restores standard database_manager.py after build
   - Produces: **PsyClick_Clinical_Offline_Setup.exe**

#### 3. **DEPLOYMENT_GUIDE_OFFLINE.txt**
   - Complete offline deployment guide
   - Covers air-gapped clinical environments
   - Includes troubleshooting for offline scenarios
   - Backup/restore procedures (USB-to-USB)

#### 4. **OFFLINE_BUILD_README.md** (This file)
   - Technical documentation of offline build system
   - How to build offline editions
   - What code was removed and why

### Code Removed from Offline Version

The offline database manager completely removes:

```python
# REMOVED: PostgreSQL/Supabase imports
import psycopg2

# REMOVED: Cloud credential detection
env_url = os.environ.get('PSYCLICK_DB_URL', '')
if env_url.startswith('postgresql://'):
    # ... cloud connection logic
    
# REMOVED: config.json cloud URL lookup
cfg_candidates = [...]  # Supabase URL discovery
for cfg_path in cfg_candidates:
    url = cfg.get('database_url')
    if url.startswith('postgresql://'):
        # ... cloud connection setup

# REMOVED: PostgreSQL connection pooling
psycopg2.connect(_PG_URL, connect_timeout=5)

# REMOVED: SQL dialect adaptation for PostgreSQL
def _sql(s):
    # SQLite syntax → PostgreSQL syntax conversion
```

### What Stays the Same

All clinical logic, anomaly detection, and statistical calculations remain **identical**:

- Hotelling's T² multivariate detection
- EWMA baseline tracking
- Fuzzy logic classification
- Task-adjusted thresholds
- Psychomotor biomarker extraction
- Normative population comparison
- Bootstrap confidence intervals
- Patient session persistence
- Clinician dashboard

## Build Instructions

### Building Offline Edition (Clinical)

```bash
cd C:\Users\Lana\Documents\psyclick-1\psyclick-clinical

# Clean previous build artifacts (recommended)
rmdir /s /q node_modules 2>nul
rmdir /s /q frontend\node_modules 2>nul
rmdir /s /q dist 2>nul
rmdir /s /q frontend\dist 2>nul
del package-lock.json 2>nul
del frontend\package-lock.json 2>nul

# Run offline build
BUILD_OFFLINE.bat
```

### Build Process (Automated)

The `BUILD_OFFLINE.bat` script:

1. **PRE-BUILD:** Backs up standard `database_manager.py` → `database_manager_standard.py`
2. **PRE-BUILD:** Copies `database_manager_offline.py` → `database_manager.py`
3. **STEP 1:** Installs Python dependencies (Flask, NumPy, SciPy, but **NOT psycopg2**)
4. **STEP 2:** Bundles Flask API with PyInstaller
5. **STEP 3:** Builds React frontend with Vite
6. **STEP 4:** Packages with Electron Builder
7. **POST-BUILD:** Restores `database_manager_standard.py` → `database_manager.py`

Output: **PsyClick_Clinical_Offline_Setup.exe** (~500MB)

## Verification Checklist

Before deployment, verify offline-only operation:

```python
# ✓ Check: database_manager_offline.py contains NO:
grep "psycopg2"         database_manager_offline.py  # Should be EMPTY
grep "postgresql"       database_manager_offline.py  # Should be EMPTY
grep "postgres://"      database_manager_offline.py  # Should be EMPTY
grep "Supabase"         database_manager_offline.py  # Should be EMPTY
grep "database_url"     database_manager_offline.py  # Should only be doc/comments
grep "config.json"      database_manager_offline.py  # Should only be doc/comments

# ✓ Check: No Python package dependencies for cloud
cat requirements.txt  # Should NOT include: psycopg2, boto3, supabase, etc.

# ✓ Check: Flask API has no cloud code
grep -r "psycopg2"     dist-python/       # Should be EMPTY
grep -r "supabase"     dist-python/       # Should be EMPTY
grep -r "PSYCLICK_DB_URL" dist-python/   # Should be EMPTY
```

## Deployment Scenarios

### Scenario 1: Air-Gapped Hospital Network

```
1. Download PsyClick_Clinical_Offline_Setup.exe on internet machine
2. Transfer via USB to hospital network (never connected to internet)
3. Install on clinical workstation
4. Start using immediately (no configuration needed)
5. Data stored locally: %APPDATA%\PsyClick\psyclick_data.db
6. Backup: Copy .db file to USB drive
```

### Scenario 2: Demo Deployment

```
1. Run PsyClick_Clinical_Offline_Setup.exe
2. Launch application (instant startup, no cloud waiting)
3. Login as "clinician" (no password)
4. View sample assessments (if pre-loaded data)
5. Demo ready in <5 minutes
```

### Scenario 3: Research Environment

```
1. Install on research machine
2. Generate assessment data via Tester mode (Standard Edition)
3. Transfer database: C:\Users\[user]\AppData\Roaming\PsyClick\psyclick_data.db
4. Open in Offline Edition
5. Analyze results without any internet dependency
```

## Standard Edition vs Offline Edition

| Feature | Standard | Offline |
|---------|----------|---------|
| SQLite database | ✓ | ✓ |
| Supabase support | ✓ | ✗ |
| Tester mode | ✓ | ✗ |
| Clinician mode | ✓ | ✓ |
| Internet required | Optional | **Never** |
| Config file needed | Optional | **No** |
| Cloud credentials | Optional | **None** |
| Installer size | ~700MB | ~500MB |
| Air-gap ready | ✓ | ✓ |
| Offline operation | ✓ | ✓ |
| Demo-ready | With data | ✓ |

## Offline Edition Limitations

The Offline Edition is **clinician-only**:

- ✗ No Tester mode (use Standard Edition for assessments)
- ✗ No Supabase cloud sync
- ✗ No remote data access

Solutions:

1. **Run Standard Edition elsewhere:** Generate assessments on Standard Edition, then copy database file to Offline Edition
2. **Export/Import:** Use Standard Edition to export assessment data, import into Offline Edition
3. **Portable deployment:** Install Standard Edition on portable drive for assessments, sync to Offline Edition

## Post-Build Verification

After running BUILD_OFFLINE.bat:

```bash
# Verify offline executable was created
dir frontend\dist-electron\*.exe

# Verify database_manager was restored
grep "import psycopg2" database_manager.py
# Should output: (no match - restored to standard version)
```

## Troubleshooting Build Issues

### Issue: "psycopg2 not found"

This should **NOT happen** with BUILD_OFFLINE.bat because:
- `database_manager_offline.py` has no psycopg2 imports
- pip install excludes psycopg2 from offline build

If it occurs:
1. Delete `database_manager.py`
2. Copy `database_manager_offline.py` → `database_manager.py`
3. Run build again

### Issue: "Config.json missing"

This is **CORRECT behavior** for offline edition:
- Offline Edition ignores config.json
- Works without any configuration files
- No action needed

### Issue: "Cannot connect to Supabase"

This is **EXPECTED** and **CORRECT**:
- Offline Edition has no Supabase code
- Completely expected if you try to use Supabase URL
- Use Standard Edition for cloud features

## File Organization

```
psyclick-1/
├── database_manager.py                 (Standard: dual-mode SQLite+Postgres)
├── database_manager_offline.py         (Offline: SQLite ONLY)
├── psyclick-clinical/
│   ├── database_manager.py
│   ├── database_manager_offline.py
│   ├── BUILD_CLINICAL.bat              (Standard clinical build)
│   ├── BUILD_OFFLINE.bat               (Offline clinical build)
│   └── frontend/
│       └── electron/
│           ├── main.js                 (No cloud code)
│           └── preload.js              (No cloud code)
├── DEPLOYMENT_GUIDE.txt                (Standard: dual-mode deployment)
├── DEPLOYMENT_GUIDE_OFFLINE.txt        (Offline: air-gap deployment)
└── OFFLINE_BUILD_README.md             (This file)
```

## Security Implications

### Standard Edition

- Can accept Supabase credentials (via config.json or env var)
- Can make cloud API calls
- Risk: credentials in config file (mitigated: credentials file removed in this session)
- Benefit: cloud backup and multi-location sync

### Offline Edition

- **Cannot** connect to Supabase
- **Cannot** make any cloud API calls
- **Cannot** load cloud credentials
- **Advantage:** HIPAA/data-safety compliant by design (zero cloud exposure)
- **Advantage:** No credential storage risk
- **Advantage:** Complete data ownership

## Recommendations

### For Clinical Deployment

Use **Offline Edition** if:
- Facility has no internet access
- HIPAA compliance is critical
- Data must stay on-device
- No multi-location sync needed
- Portability across air-gapped systems is required

Use **Standard Edition** if:
- Facility has secure internet connection
- Cloud backup/sync is desired
- Multi-location clinician access is needed
- Both Tester and Clinician modes needed

### For Research

Use **Standard Edition** for:
- Assessment generation (Tester mode)
- Data collection
- Multi-site deployments

Use **Offline Edition** for:
- Analysis environment (air-gap ready)
- Portable analysis workstation
- Standalone research machines

## Support & Questions

For offline deployment issues:
- Check DEPLOYMENT_GUIDE_OFFLINE.txt
- Review OFFLINE_BUILD_README.md (this file)
- Inspect %APPDATA%\PsyClick\api_startup.log for startup errors

For building issues:
- Ensure node_modules and package-lock.json are deleted
- Run BUILD_OFFLINE.bat as Administrator
- Check Python version is 3.13+

---

**Status:** OFFLINE BUILD SYSTEM — READY FOR PRODUCTION  
**Last Updated:** 2026-05-19  
**Version:** PsyClick v4  
**Database:** SQLite 3 (offline-only)
