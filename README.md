# CloudLog Analytics: Cloud-Based Web Log Analysis Using MapReduce

CloudLog Analytics is a cloud computing college project demonstrating distributed data processing principles on web server access logs. It replaces commercial cloud virtual machines (such as paid Amazon EC2 instances) and complex multi-node cluster administration (such as Apache Hadoop) with an educational single-host MapReduce engine deployed to free **Streamlit Community Cloud**.

---

## 1. Project Overview & Architectural Concepts

- **MapReduce Paradigm**: Implements the classic five-stage distributed data processing workflow:
  1. **Partitioning**: Slices input log records into disjoint chunks.
  2. **Mapping**: Pure, top-level picklable worker functions transform raw records into uniform key-value pairs `(key, (count=1, error_count, response_time_ms))`.
  3. **Shuffling & Grouping**: Accumulates and groups emitted values across all partition streams by key.
  4. **Associative Reduction**: Aggregates counts, error counts, and latency sums.
  5. **Metric Derivation**: Derives weighted mean latencies (`total_latency_sum / total_requests`) and error percentages, preventing statistical distortion (such as Simpson's paradox from unweighted partition averages).
- **Dual Execution Modes**:
  - **Serial Mode**: Single-process linear pipeline for baseline comparisons.
  - **Parallel Mode**: Multi-worker execution leveraging Python's `concurrent.futures.ProcessPoolExecutor` with automatic graceful fallback to serial execution if worker pool limits are encountered.
- **Zero Cost & Free Cloud Hosting**: Built entirely with open-source tools (Python 3.10/3.11, Streamlit, Pandas, Plotly, Pytest) designed for deployment on free Streamlit Community Cloud.

---

## 2. CSV Schema & Ingestion Specifications

The application accepts standard web server log CSV files with the following schema:

| Column | Type | Description | Validation Rule |
| :--- | :--- | :--- | :--- |
| `timestamp` | String | UTC ISO 8601 or standard datetime | Must parse to valid UTC datetime; rejection on malformed date |
| `endpoint` | String | HTTP request path (e.g. `/api/v1/catalog`) | Non-empty string; trimmed; rejection on blank/whitespace |
| `method` | String | HTTP verb (e.g. `GET`, `POST`) | Member of `{GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS}` |
| `status_code` | Integer | HTTP response status (e.g. `200`, `500`) | Integer in range `[100, 599]` |
| `response_time_ms` | Float | Server execution latency in milliseconds | Finite numeric value $\ge 0.0$ (no `NaN`, `-Inf`, or negative) |

### Ingestion Safety Ceilings
- **Maximum File Upload Size**: `5.0 MB` (enforced in both Streamlit server configuration and payload validator).
- **Maximum Row Processing Limit**: `50,000 rows` (prevents memory exhaustion in shared cloud containers).

---

## 3. Quick Start & Setup Instructions

### Prerequisites
- Python 3.10 or Python 3.11 installed.
- Git installed.

### Option A: Windows PowerShell Setup

```powershell
# 1. Clone or navigate to the repository
cd "c:\Users\soham\OneDrive\Desktop\cloud computing project"

# 2. Create and activate a virtual environment (Python 3.11 preferred)
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Upgrade pip and install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 4. Generate the default synthetic dataset (~5,000 rows)
python -m data.generate_sample

# 5. Launch the Streamlit application
python -m streamlit run app.py
```

### Option B: macOS / Linux (bash/zsh) Setup

```bash
# 1. Clone and navigate to project directory
cd /path/to/cloud-computing-project

# 2. Create and activate virtual environment (Python 3.11 preferred)
python3.11 -m venv .venv
source .venv/bin/activate

# 3. Upgrade pip and install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 4. Generate sample dataset
python -m data.generate_sample

# 5. Launch the Streamlit application
python -m streamlit run app.py
```

The application will be accessible at `http://localhost:8501`.

---

## 4. Running the Automated Test Suite

The test suite covers schema validation, boundary enforcement, uneven partition handling, weighted mean accuracy, serial vs parallel equivalence, independent reference aggregation (Pandas groupby), forced process pool failure fallback, and programmatic UI integration tests via `AppTest`.

```powershell
# Run the complete test suite
python -m pytest -v

# Run only MapReduce & equivalence tests
python -m pytest tests/test_mapreduce.py tests/test_equivalence.py -v
```

---

## 5. Visual Design & Editorial Palette

The user interface follows a restrained, professional design system strictly free of generic AI-generated clichés (no gradients, no neon, no emojis in headings, no pill-shaped containers):

- **Main Background**: Warm Ivory (`#F7F5F0`)
- **Card Surfaces**: Pure White (`#FFFFFF`)
- **Primary Text**: Charcoal (`#252823`)
- **Primary Accent**: Dark Olive (`#526044`)
- **Error / Highlight**: Muted Terracotta (`#B65C3A`)
- **Supporting Accents**: Ochre (`#C49A45`), Sage (`#7A8B6E`), Stone (`#6B705C`)
- **Borders**: Warm Gray (`#E2DFD8`)
- **Color Restrictions**: **Zero blue or purple** is utilized anywhere in charts, links, focus outlines, or styles.

---

## 6. Cloud Architecture & Deployment Instructions

### Architecture Overview
```
[Client Web Browser]
       │
       ▼ (HTTPS / WebSocket)
[Streamlit Community Cloud (Managed PaaS Container)]
       │
       ▼ (Schema Validation & 5MB/50k Row Guard)
[cloudlog.validator]
       │
       ▼ (Partitioning -> Map Worker Processes)
[cloudlog.mapreduce (Top-level Picklable Workers)]
       │
       ▼ (Shuffle & Group by Key)
[In-Memory Hash-Group Aggregation]
       │
       ▼ (Associative Reduction & Metric Derivation)
[Weighted Means & Error Percentage Derivations]
       │
       ▼ (Plotly Custom Themed Visuals & CSV Export)
[Interactive Dashboard Presentation]
```

### Managed PaaS (Streamlit Cloud) vs. IaaS (Amazon EC2)

| Feature | Streamlit Community Cloud (Managed PaaS) | Amazon EC2 (Self-Managed IaaS) |
| :--- | :--- | :--- |
| **Operational Overhead** | Zero Linux/VM administration; automated deployment from Git | Requires OS patching, security groups, SSH key management |
| **Financial Cost** | 100% Free tier (no credit card or billing risk) | Requires AWS account, billing alerts, risk of runaway costs |
| **Container Lifecycle** | Ephemeral serverless container (sleeps when idle, cold starts) | Persistent virtual machine running 24/7 until stopped |
| **Data Storage** | Transient in-memory state; uploads discarded on session close | Durable EBS block storage attached to instance |
| **Educational Focus** | Rapid focus on algorithmic MapReduce & analytics logic | Focuses on Linux infrastructure and networking setup |

### Free Streamlit Community Cloud Deployment Steps

1. **Commit Code to GitHub**:
   - Create a new public or private repository on GitHub (e.g., `cloudlog-analytics`).
   - Push your project code:
     ```bash
     git init
     git add .
     git commit -m "Initial commit of CloudLog Analytics"
     git branch -M main
     git remote add origin https://github.com/<your-username>/cloudlog-analytics.git
     git push -u origin main
     ```
2. **Deploy on Streamlit Community Cloud**:
   - Go to [share.streamlit.io](https://share.streamlit.io/) and sign in with your GitHub account.
   - Click **"New app"**.
   - Select your repository (`<your-username>/cloudlog-analytics`), branch (`main`), and main file path (`app.py`).
   - Click **"Deploy!"**.
   - Streamlit will read `requirements.txt` and `.streamlit/config.toml`, install dependencies, and launch your live application at `https://<your-app-name>.streamlit.app`.

---

## 7. Honest Technical Boundaries & Limitations

1. **Single-Host Teaching Pipeline**: This implementation runs on a single host using Python multiprocessing. It is not an Apache Hadoop cluster across rack-mounted physical nodes. There is no HDFS or YARN resource manager.
2. **Transient In-Memory State**: Uploaded CSV files are processed in ephemeral RAM buffers and are **never** persisted to durable disk or third-party cloud storage.
3. **Multiprocessing Overhead on Small Datasets**: In benchmarks, serial mode is often faster than 2-process mode on datasets under 10,000 records. This is an authentic systems reality: OS process spawn time, dictionary serialization (pickling), and IPC overhead outweigh parallel CPU gains for small jobs. Measured execution times are observations from this specific host machine, not universal performance guarantees.
4. **Observed Latency vs. Contractual SLA**: Measured processing times in the UI are observed container runtimes on this host machine. They do not constitute an uptime or latency SLA guarantee.
5. **Numerical Tolerances**: Benchmark comparisons enforce exact integer count equality, a tolerance of 0.01 ms for latencies, and 0.01 percentage points for percentage metrics.
