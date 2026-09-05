# ⚡ MailAccess Studio: Next-Gen Email OSINT Suite

[![Python Version](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-v3.0-38B2AC.svg)](https://tailwindcss.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> A modern, fast, and high-tech OSINT (Open-Source Intelligence) email reconnaissance suite with real-time SSE telemetry streaming and interactive identity profiling.

---

## ✨ Key Features

- **⚡ Real-Time Module Matrix**: Inspired by terminal-style OSINT suites, features a live streaming module execution table with sub-second response times.
- **👤 Target Identity Dossier & Avatar**:
  - Automatically recovers Git commit signatures, author names, and Gravatar profiles.
  - Smart Indian & Global name tokenizer (splits First, Middle, Last names and handles compound variations like *Yash Raj Gupta* vs. *Yashraj Gupta*).
  - High-res avatar fallback engine with verified status rings.
- **🌐 Verified Platform Discovery (Zero False Positives)**:
  - Probes **GitHub**, **Instagram**, **Threads**, **X (formerly Twitter)**, **Spotify**, **Duolingo**, **Chess.com**, **Docker Hub**, and **Dev.to**.
  - Displays **only confirmed positive hits** with direct profile links (`Visit Profile ↗`).
- **🛡️ Infostealer Malware Audit**: Integrates with Hudson Rock's Cavalier API to detect if credentials for the email were compromised in stealer malware logs (RedLine, Lumma, Vidar, etc.).
- **🔍 Domain & Deliverability Intel**: Verifies MX records, disposable email addresses, and generates targeted one-click Google Dorks.

---

## 🚀 Quickstart

### Prerequisites
- Python 3.9+ installed
- Git installed

### Installation & Run

1. **Clone the repository:**
   ```bash
   git clone https://github.com/priyank0777/mailaccess.git
   cd mailaccess-studio
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
3. **Start the Dashboard:**
   ```bash
   python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
4. **Open your browser at:**
   ```bash
   http://127.0.0.1:8000
