# PRD.md

# Product Requirements Document: CareerFit Radar

## 1. Product Name

CareerFit Radar

---

## 2. Product Goal

CareerFit Radar is an AI-powered job intelligence platform that helps job seekers find, evaluate, and prioritize high-fit opportunities.

The platform will:

* Discover jobs from approved public sources.
* Compare jobs against a candidate’s resume using semantic matching.
* Identify high-fit opportunities and skill gaps.
* Generate explainable fit scores.
* Recommend resume-tailoring improvements.
* Deduplicate and prioritize listings.
* Track application progress.
* Operate entirely on Google Cloud Platform.

The platform is not a job scraper, outreach tool, or auto-apply system.

---

## 3. Core Features

### Resume Intelligence

* Upload PDF or DOCX resumes.
* Extract structured candidate profiles.
* Identify skills, experience, projects, and target roles.
* Generate embeddings for semantic matching.

### Job Discovery

* Collect jobs from approved public sources:

  * Greenhouse
  * Lever
  * Remotive
  * Arbeitnow
* Normalize and store job data.
* Maintain source execution logs.

### Filtering and Deduplication

* Reject unsuitable jobs before AI processing.
* Remove duplicate listings using metadata and embeddings.
* Preserve rejection reasons and allow manual review.

### AI-Powered Matching

* Extract job requirements.
* Generate embeddings using Gemini.
* Match resumes against job descriptions and requirements.
* Cache embeddings and avoid unnecessary reprocessing.

### Fit Scoring

Score jobs from 0–100 using:

| Category            | Weight |
| ------------------- | ------ |
| Role Match          | 15     |
| Skill Match         | 20     |
| Semantic Similarity | 20     |
| Experience Fit      | 15     |
| Freshness           | 15     |
| Location Fit        | 10     |
| Source Reliability  | 5      |

Score bands:

| Score    | Meaning           |
| -------- | ----------------- |
| 85–100   | Apply Immediately |
| 70–84    | Strong Match      |
| 55–69    | Possible Match    |
| 40–54    | Weak Match        |
| Below 40 | Reject            |

All scores must be explainable.

### Gap Analysis

For shortlisted jobs:

* Matched skills
* Missing skills
* Partial matches
* Relevant projects
* Risk areas
* Resume-tailoring recommendations

The system must never invent skills or experience.

### Daily Shortlist

Generate a prioritized shortlist including:

* High-fit jobs
* Remote jobs
* Relocation-friendly jobs
* Stretch opportunities

Each job includes:

* Company
* Location
* Posted date
* Fit score
* Match explanation
* Apply URL
* Application status

### Application Tracking

Track:

* Saved
* Applied
* Follow-Up Needed
* Interview
* Rejected
* Offer
* Ignored

### Search and Export

Support:

* Keyword search
* Semantic search
* Similar-job search
* CSV and Excel export

---

## 4. Non-Goals

The platform must not:

* Auto-apply to jobs.
* Send automated emails or outreach.
* Scrape LinkedIn, Indeed, Naukri, or Glassdoor.
* Access login-protected systems.
* Bypass CAPTCHA or robots.txt restrictions.
* Store private ATS data.
* Depend on paid job APIs.
* Become a generic scraping platform.

---

## 5. MVP Scope

The MVP includes:

* Resume upload and parsing
* Candidate profile extraction
* Greenhouse integration
* Lever integration
* Remotive integration
* Arbeitnow integration
* PostgreSQL storage with pgvector
* Gemini embeddings
* Gemini requirement extraction
* LangGraph workflow orchestration
* Hard filtering
* Deduplication
* Fit scoring
* Gap analysis
* Daily shortlist generation
* Streamlit dashboard
* Application tracker
* CSV export
* Google Cloud Run deployment
* Cloud Scheduler integration
* Secret Manager integration

---

## 6. Success Criteria

### Product Success

* Reduce job-search effort.
* Improve job relevance.
* Increase focus on high-probability opportunities.
* Provide clear fit explanations.
* Improve application organization.

### Technical Success

* At least four job sources integrated.
* Reliable duplicate detection.
* Explainable scoring system.
* Functional pgvector semantic search.
* Reliable LangGraph execution.
* Logged failures and workflow visibility.
* Fully hosted on Google Cloud Platform.

---

## 7. Final Positioning

CareerFit Radar is a cloud-native AI job intelligence platform built on Google Cloud Platform using FastAPI, LangGraph, Gemini models, PostgreSQL, and pgvector.

It continuously discovers fresh opportunities, removes low-value listings, performs semantic resume matching, explains fit scores, identifies skill gaps, and helps candidates focus on opportunities most likely to generate interviews.

Core principle:

> Help users submit better applications, not more applications.

The product prioritizes usefulness, accuracy, and transparency over automation.
