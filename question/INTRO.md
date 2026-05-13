# Telemetry Analysis Case Study

## Overview

Welcome to this telemetry analysis case study. You have been provided
with a dataset containing telemetry data from a microservice-based system. Your
task is to analyze this data to understand the system's behavior, identify
patterns and anomalies, and provide recommendations for improvement.

This case study is designed to evaluate your:

- Analytical and problem-solving skills
- Ability to work with time-series data
- Understanding of distributed systems and observability
- Written communication skills
- Technical proficiency with data analysis tools
- **Most importantly: Your judgment in identifying what matters most**

## Dataset Description

You have been provided with a CSV file (`data/telemetry_dataset.csv`) containing
telemetry events from a production microservice. Each row represents a single
request-response exchange between a client and a service instance.

The dataset contains the following fields:

- `timestamp`: When the request occurred (RFC8601 format)
- `client_id`: Unique identifier for the client making the request
- `server_id`: Identifier of the service instance that handled the request
- `request_type`: HTTP method (GET, POST, PUT, DELETE, etc.)
- `request_url`: The API endpoint accessed
- `response_status_code`: HTTP response status code
- `request_id`: Unique identifier for the request (UUIDv4)
- `response_id`: Unique identifier for the response (UUIDv4)
- `agent_name`: Client user agent/browser
- `client_device_type`: Type of client device (desktop, mobile, other)
- `duration`: Request processing time in microseconds
- `response_size`: Size of the response payload in bytes
- `request_size`: Size of the request payload in bytes
- `geographic_region`: Geographic region of the client

## Important

**This case study is intentionally open-ended.** The questions and topics below
are suggestions and starting points for exploration, not a checklist to complete
exhaustively. We value depth over breadth—it's far better to provide
meaningful insights on a few important findings than to superficially cover
everything.

**Use your professional judgment to:**

- Identify what aspects of the data are most interesting or concerning
- Decide where to focus your analysis based on what you discover
- Prioritize findings that would matter most in a real production scenario
- Skip areas that don't yield interesting insights after initial exploration

Think of this as analyzing a real production system where you need to deliver
actionable insights within time constraints. What would you investigate first?
What would provide the most value to the engineering team?

## Suggested Areas for Investigation

The following sections provide potential directions for your analysis. Choose
the areas that you find most compelling or where you discover the most
significant patterns.

### Part 1: Exploratory Data Analysis

Consider investigating aspects such as:

1. **System Characteristics**
    - How many service instances are represented in the data?
    - What is the time span covered by the dataset?
    - What API endpoints are being accessed?
    - What is the overall request volume and distribution?

2. **Traffic Patterns**
    - How is traffic distributed across service instances?
    - Are there any temporal patterns in the request volume?
    - What is the distribution of request types (GET, POST, etc.)?
    - How are clients distributed (80/20 rule, geographic distribution, device
      types)?

3. **Performance Analysis**
    - What are the response time characteristics (median, p95, p99)?
    - How do response times vary by:
        - Service instance
        - Request type
        - Geographic region
        - Time period
    - Are there any performance outliers or degradations?

4. **Error Analysis**
    - What types of errors occur in the system?
    - What is the error rate over time?
    - Are errors correlated with specific service instances, endpoints, or time
      periods?

### Part 2: Incident Detection and Analysis

Examine the dataset for any incidents or anomalies:

1. **Identify Incidents**
    - Are there any periods of service degradation or failure?
    - Can you identify the timeline and impact of each incident?
    - What are the characteristics of each incident (error types, affected
      services, duration)?

2. **Root Cause Analysis**
    - Based on the telemetry data, what might have caused each incident?
    - Which service instances were affected?
    - How did the system recover?

3. **Impact Assessment**
    - How many requests were affected during each incident?
    - What was the customer impact (error rates, latency degradation)?
    - Were certain client segments more affected than others?

### Part 3: System Design and Monitoring Recommendations

Based on your analysis, provide thoughtful recommendations on the following
topics:

1. **Monitoring and Observability**
    - What key metrics would you monitor for this system?
    - What alerts would you configure to detect similar incidents early?
    - What additional telemetry would be valuable to collect?

2. **Service Level Objectives (SLOs)**
    - Propose appropriate SLOs for this service based on the observed behavior
    - What SLI (Service Level Indicator) metrics would you track?
    - What error budget would you recommend?

3. **System Improvements**
    - What architectural or operational changes would you recommend to improve:
        - System reliability
        - Performance
        - Incident detection and response
    - How would you handle the traffic patterns you observed?
    - What strategies would you employ to prevent or mitigate the incidents you
      identified?

4. **Capacity Planning**
    - Based on the traffic patterns, what recommendations would you make for:
        - Service instance scaling
        - Geographic distribution
        - Load balancing strategies

## Deliverables

Please provide:

1. **Analysis Report** (Required)
    - A written report (Markdown, PDF, or HTML) documenting your findings
    - Clear visualizations supporting your analysis
    - Focus on the areas you chose to investigate deeply
    - Executive summary of key findings and recommendations

2. **Analysis Code** (Required)
    - All scripts, notebooks, or code used in your analysis
    - Clear documentation or comments explaining your approach
    - Instructions for reproducing your analysis

3. **Supporting Materials** (Optional but encouraged)
    - Dashboards or interactive visualizations
    - Additional data transformations or derived metrics
    - Proposed monitoring configurations or alert rules

## Technical Guidelines

- You may use any programming language, tools, or frameworks you're comfortable
  with
- Popular choices include Python (pandas, polars, matplotlib, seaborn), R, SQL,
  or specialized tools like Grafana
- Jupyter notebooks are welcome for combining code and analysis
- Consider using data profiling tools for initial exploration

### Use of AI Tools

You are encouraged to use AI tools and agents (ChatGPT, Claude, Copilot, etc.)
to assist with your analysis. If you do:

- Document which tools/models you used
- Include the prompts you used for significant analysis or code generation
- Clearly indicate which portions were AI-assisted
- These form part of your "source code" and help us understand your
  problem-solving approach

## Evaluation Criteria

Some of the criteria your submission will be evaluated on are listed below:

1. **Judgment and Focus**
    - Ability to identify what matters most in the data
    - Quality of insights over quantity of analysis
    - Appropriate prioritization of investigation areas

2. **Technical Analysis**
    - Accuracy and depth of chosen analyses
    - Appropriate use of statistical methods and visualizations
    - Ability to identify meaningful patterns and anomalies

3. **Problem Solving**
    - Quality of recommendations based on findings
    - Understanding of distributed systems and monitoring best practices
    - Practicality of proposed solutions

4. **Communication**
    - Clarity and organization of the written report
    - Quality of visualizations and their explanatory power
    - Ability to convey technical findings effectively

## Time Expectation

This case study is designed to take approximately 4–6 hours to complete. We
value quality over quantity—focus on demonstrating your analytical skills and
thought process rather than exhaustive analysis of every possible angle.

## Submission Instructions

Please submit your completed analysis as a compressed archive (ZIP or TAR.GZ)
containing:

- Your analysis report
- All code and notebooks
- Any additional materials
- A README file with instructions for reviewing your work

## Questions?

If you have any questions about the case study requirements or encounter issues
with the dataset, please reach out to your recruiting contact.

Good luck, and we look forward to reviewing your analysis!

---

*Note: This synthetic dataset represents a snapshot of production telemetry
data. While analyzing real-world patterns, remember that production systems
are complex and the full context may not be captured in this limited dataset.*
