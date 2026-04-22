<p align="center">
  <img src="neurocomputer/assets/neuro.png" width="80" height="80" alt="Neurocomputer Logo">
</p>

<h1 align="center">Neurocomputer</h1>
<p align="center"><strong>The Agentic Masterpiece Framework.</strong></p>
<p align="center">A profoundly theoretical and practical pathway to Agency AI, combining deep mathematical R&D with a highly optimized OS-level automation ecosystem.</p>

<p align="center">
  <a href="https://neurocomputer.in">Website</a> · <a href="#agency-ai---the-evolutionary-leap">Agency AI</a> · <a href="#deep-rd--mathematical-foundations">Deep R&D</a> · <a href="#the-neuro-framework">Framework</a> · <a href="#os-applications--the-practical-layer">OS Apps</a> · <a href="#quick-start">Quick Start</a>
</p>

---

## 🌌 The Vision: Agency AI

Computing is undergoing a fundamental paradigm shift. We have moved beyond monolithic models into a new era of hierarchical intelligence. The evolutionary timeline is clear:

1. **Software** ➔ Hardcoded logic and rigid rules.
2. **Statistical ML** ➔ Probabilistic pattern recognition.
3. **Generative Models** ➔ Token prediction and transformers (LLMs).
4. **Reasoning Models** ➔ Chain-of-Thought execution and state maintenance.
5. **Agentic Systems** ➔ Autonomous loops that observe, reason, and act across domains.
6. **Agency AI (Our Vision)** ➔ Hierarchical, modular *agencies* that contain specialized, shared *agents*. An abstract, infinitely modifiable, and scalable network of intelligence.

Neurocomputer aims to build the mathematical and software framework to make **Agency AI** a reality.

---

## 🔬 Deep R&D & Mathematical Foundations

We are an organization committed to solving the hardest research problems in AI training and inference. We do not believe brute-force scaling is the final answer to AGI.

Instead, we are leveraging **deeper mathematical tools**—inspired by quantum physics and higher-dimensional geometry—to build models and agency structures that are:
- **Transparent**: Moving away from "black box" inference to mathematically provable pathways using graphs.
- **Efficient**: Drastically faster and more resource-sensitive for general-purpose use.
- **Entropy-Aware**: Using entropy-based evaluation principles to actively measure and reduce inefficiencies, complexity, and computational waste during system self-modification.

---

## 🧠 The Neuro Framework

The practical core of Neurocomputer is a modular platform for creating AI systems that learn, adapt, and improve. 

- **Neuro**: The basic building block. A lightweight module capable of storing information, executing logic, making decisions, and handling data I/O.
- **Neuro-Net**: The flexible network connecting neuros, forming strict, structured pathways for complex tasks.
- **Neuro-Lang & Neuro-Compiler**: A simple orchestration language that compiles down into error-free, optimized executables, allowing humans and AI to co-develop workflows.
- **Neuro-Dream**: A background process that aggregates incremental changes and experiences, fine-tuning and optimizing the AI agencies automatically without interrupting operation.

---

## 🖥️ OS Applications (The Practical Layer)

While we research the profound theoretical foundations of Agency AI, we are simultaneously building the **Application Layer**—treating the Neuro framework like a futuristic Operating System where agents are isolated, highly specialized "Apps" with their own runtimes.

These apps are fully open-source, well-tested, and ready to use today:

| App / Agent | What It Does |
|---|---|
| **Neuro** | The general-purpose core. Routes intents, plans tasks, and orchestrates skills. |
| **OpenClaw** | Browser automation. Connects to a local gateway to physically browse the web, click elements, and extract data autonomously. |
| **OpenCode** | The developer's companion. Reads, writes, diffs, and patches code across entire repositories. |
| **NeuroUpwork** | The freelance engine. Scrapes job listings, scores them, and drafts tailored proposals and Proof-of-Concepts. |
| **Mobile Remote** | A React/Kotlin smart remote interface that streams your desktop and runs these OS Apps in real-time over LiveKit. |

---

## 🚀 Quick Start (Running the OS)

Neurocomputer isolates these OS Apps into a secure sandbox, preventing AI models from blindly modifying your personal host OS. 

### 1. Clone & Install

```bash
git clone https://github.com/neurocomputer-in/neurocomputer.git
cd neurocomputer
python3 -m venv venv && source venv/bin/activate
pip install -r neurocomputer/requirements.txt
```

### 2. Configure Your Environment

Create a `.env` file securely holding your API keys:

```dotenv
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...
SARVAM_API_KEY=...
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
```

Run your local LiveKit server (highly recommended for real-time WebRTC connections):
```bash
cp neurocomputer/livekit.yaml.example livekit.yaml
livekit-server --config livekit.yaml &
```

### 3. Start the Neuro OS Runtime

```bash
python neurocomputer/server.py
# Server starts at http://0.0.0.0:8000
```

Wait for the engine to initialize, and connect your Android app or web client to issue commands directly to the Agent Apps in the ecosystem.

---

<p align="center"><sub>Driven by Mathematics. Built for the Future.</sub></p>
