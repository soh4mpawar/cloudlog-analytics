# CloudLog Analytics: 10-Minute Demonstration Script

This demonstration script is designed for a **10-minute university presentation and viva demonstration** of CloudLog Analytics. It includes cue-by-cue timing, screen actions, and role allocations for either a **2-student team** or a **3-student team**.

---

## Team Role Allocation Matrix

| Demo Segment | Time | 2-Student Team | 3-Student Team | Focus Area |
| :--- | :--- | :--- | :--- | :--- |
| **1. Introduction & Context** | 0:00 – 1:30 | **Student A** | **Student 1** | Problem statement, cloud context, architecture |
| **2. Live Dashboard & Ingestion** | 1:30 – 4:00 | **Student A** | **Student 2** | Operational analytics, filters, schema validation |
| **3. Inside MapReduce Deep-Dive** | 4:00 – 6:30 | **Student B** | **Student 3** | 5-stage pipeline, math integrity, worker models |
| **4. Benchmark & Performance** | 6:30 – 8:30 | **Student B** | **Student 2** | Serial vs parallel, IPC overhead, empirical timing |
| **5. Cloud Architecture & Viva** | 8:30 – 10:00 | **Student A & B** | **Student 1 & 3** | PaaS vs IaaS, SLA vs latency, limitations, Q&A |

---

## Timed Walkthrough Script

### Minute 0:00 – 1:30: Introduction & Architectural Overview
- **Speaker**: Student 1 (or Student A)
- **Screen Action**: Display application home screen on `http://localhost:8501` (Dashboard view with default 5,000 logs).
- **Spoken Script**:
  > *"Good morning, Professors. Today we present **CloudLog Analytics**, a cloud-based web log analysis platform built using the MapReduce paradigm.
  > 
  > In real-world cloud environments, web servers generate hundreds of thousands of HTTP access logs per minute. To monitor system health, detect 4xx/5xx error anomalies, and track endpoint latencies, systems traditionally rely on massive distributed clusters like Apache Hadoop or Amazon EMR on EC2.
  > 
  > In this project, we achieved two main goals:
  > First, we implemented an authentic single-host MapReduce processing engine in Python using top-level worker processes, proving how partitioning, mapping, shuffling, associative reduction, and weighted derivations work under the hood.
  > Second, rather than incurring unnecessary billing on AWS EC2 virtual machines, we adapted the system for free cloud deployment on Streamlit Community Cloud using a modern serverless container model.
  > Let's look at the operational dashboard."*

---

### Minute 1:30 – 4:00: Operational Dashboard, Filters & Schema Ingestion
- **Speaker**: Student 2 (or Student A)
- **Screen Action**: 
  1. Point to the top metric strip (`Total Requests: 5,000`, `Error Rate: 7.9%`, `Mean Latency: ~87 ms`).
  2. Point to the horizontal bar chart: Requests by Endpoint.
  3. Change the endpoint filter in the sidebar (e.g., uncheck `/healthz`). Point out that metrics instantly recalculate through the MapReduce pipeline before rendering.
  4. Switch "Select Dataset" in the sidebar to "Upload CSV File". Show the schema guidance box (5 MB max, 50,000 rows max).
  5. Switch back to "Default Sample" to maintain live state.
- **Spoken Script**:
  > *"On the dashboard, all visual metrics are driven directly by our MapReduce pipeline.
  > 
  > Notice our key metrics strip: Total Requests, 4xx/5xx Error Rate, and Mean Response Time. Unlike naive dashboards that simply average averages, our pipeline derives mean response time directly from global latency sums and request counts, preserving statistical integrity.
  > 
  > The prominent horizontal bar chart visualizes request distribution across API routes like `/api/v1/catalog` and `/api/v1/orders/checkout`. Long route names remain fully legible without awkward truncation. Below it, our timeline chart breaks down hourly traffic into successful calls and error spikes in UTC.
  > 
  > In the sidebar, pre-aggregation filters allow filtering by date range or endpoint subsets. When a filter changes, the filtered record set is piped into the MapReduce engine before aggregation.
  > 
  > Our data ingestion engine enforces strict safety boundaries: a 5.0 MB file size limit and a 50,000-row processing ceiling, protecting shared cloud container memory from out-of-memory crashes."*

---

### Minute 4:00 – 6:30: Inside the MapReduce Pipeline
- **Speaker**: Student 3 (or Student B)
- **Screen Action**:
  1. Click **"Inside MapReduce"** in the sidebar.
  2. Scroll through the five numbered stages:
     - Stage 1: Partitioning (show Partition 0 and Partition 1 sizes).
     - Stage 2: Map Phase (show table of emitted `(key, (count, error, latency))` pairs).
     - Stage 3: Shuffle & Group (show table of grouped values by endpoint).
     - Stage 4: Reduce Phase (show reduced sums table).
     - Stage 5: Derive Phase (explain weighted mean formula).
- **Spoken Script**:
  > *"Now let's examine the core algorithm in the 'Inside MapReduce' view. We have structured our engine into five transparent, verifiable stages:
  > 
  > In **Stage 1 (Partitioning)**, our 5,000 validated log records are sliced into two disjoint partitions: Partition 0 with 2,500 records and Partition 1 with 2,500 records.
  > 
  > In **Stage 2 (Map Phase)**, top-level picklable worker functions transform each record into a uniform 3-tuple: `(count=1, is_error, response_time_ms)` keyed by endpoint, HTTP status code, or hourly UTC bucket. Here is a bounded sample of emitted pairs.
  > 
  > In **Stage 3 (Shuffle & Group)**, values from all partition outputs are grouped by their distinct key across partitions. This brings all latency contributions for `/api/v1/search` into a single iterable.
  > 
  > In **Stage 4 (Reduce Phase)**, the reducer computes associative sums: total requests, total errors, and cumulative latency.
  > 
  > In **Stage 5 (Derive Phase)**, we compute final analytics: `mean latency = total latency / total requests`. Crucially, this avoids Simpson's paradox: if partition sizes vary—for instance, 4 records in partition 0 and 3 in partition 1—averaging partition averages gives 184.58 ms, whereas our true weighted mean is 172.86 ms.
  > 
  > We explicitly clarify: this is an educational single-host implementation in Python using multiprocessing, not an Apache Hadoop cluster."*

---

### Minute 6:30 – 8:30: Performance Benchmark & Empirical Reality
- **Speaker**: Student 2 (or Student B)
- **Screen Action**:
  1. Click **"Benchmark"** in the sidebar.
  2. Click the button: **"Run Benchmark on Current Dataset"**.
  3. Highlight the banner: **"Verification Passed: Serial and Process executions matched across grouping keys, integer counts, and derived aggregates (tolerance: 0.01 ms for latency, 0.01 percentage points for percentage metrics)."**
  4. Point to the timing numbers (e.g. Serial: ~15–30 ms vs Parallel: ~1.5–2.8 s on Windows due to worker spawn initialization).
- **Spoken Script**:
  > *"In our Benchmark view, we execute both Serial (1 Process) and Parallel (2 Processes via `ProcessPoolExecutor`) on the exact same dataset.
  > 
  > First, look at the verification banner: our automated verification confirms that serial and parallel executions produced matching aggregations (grouping keys match, integer counts match exactly, latency averages within 0.01 ms, and percentages within 0.01 percentage points).
  > 
  > Second, observe the measured wall-clock execution time on this host. These timings are empirical observations from our machine rather than universal performance guarantees. Serial mode completed in ~15–30 ms, while 2-process parallel mode required more time.
  > 
  > Why is multiprocessing slower on 5,000 records?
  > In operating systems (particularly Windows `spawn`), creating child processes requires process creation overhead. Furthermore, Python must serialize (pickle) partitions across IPC pipes and gather results back into the parent process. We verify that worker PIDs are genuinely distinct child processes. On modest in-memory datasets, this fixed communication and process-startup cost exceeds the parallel compute savings.
  > 
  > True distributed MapReduce pays off when data volumes span tens of gigabytes or terabytes across multiple nodes that cannot fit into single-machine RAM."*

---

### Minute 8:30 – 10:00: Cloud Architecture, PaaS vs IaaS, & Q&A Conclusion
- **Speaker**: Student 1 & 3 (or Student A & B)
- **Screen Action**:
  1. Click **"Cloud Architecture"** in the sidebar.
  2. Show the comparison table: Streamlit Community Cloud vs Amazon EC2.
  3. Point to the architectural limitations and boundaries section.
- **Spoken Script**:
  > *"Finally, let's examine our cloud hosting model.
  > 
  > The original assignment guidelines suggested running on an Amazon EC2 virtual machine. By analyzing cloud trade-offs, we adopted **Streamlit Community Cloud (Managed PaaS)** over **Amazon EC2 (Self-Managed IaaS)**:
  > - **Operational Overhead**: EC2 requires manual Linux provisioning, SSH keys, security group firewall rules, and OS patching. Streamlit Cloud automatically builds and hosts the app directly from our Git repository.
  > - **Financial Feasibility**: EC2 carries billing risk and credit card requirements. Streamlit Cloud provides a genuine free tier with automated SSL certificates.
  > - **Container Lifecycles**: Our cloud container runs serverlessly, discarding transient upload state when the session terminates, ensuring user data privacy.
  > 
  > In conclusion, CloudLog Analytics provides a complete, mathematically verified, and honestly benchmarked cloud log analytics platform with 31 passing automated tests.
  > 
  > Thank you. We are now open for your questions."*
