# Agent Harness — Reading List

A curated collection of 32 articles, papers, talks, and docs on agent harness engineering: the scaffolding of tools, orchestration logic, memory, and execution infrastructure that wraps an LLM to make it capable of completing real-world tasks.

For a synthesized analysis of these sources — covering the core challenges, converging solutions, and 12 distilled best practices — see **[`report.md`](report.md)**.

Sources are grouped by theme. The original flat list lives in [`sources.md`](sources.md).

---

## 1. Foundations & Concepts

Core definitions and mental models for understanding what an agent harness is and why it matters.

- [What Is an Agent Harness?](https://www.firecrawl.dev/blog/what-is-an-agent-harness) — Firecrawl  
  An introductory explainer defining the concept: the scaffolding of tools, prompts, and execution infrastructure that wraps an LLM to make it capable of completing tasks.

- [The Anatomy of an Agent Harness](https://www.langchain.com/blog/the-anatomy-of-an-agent-harness) — LangChain  
  Dissects the structural components of a harness — tool execution, memory, routing logic, and state management — to show how each layer contributes to reliable agent behavior.

- [The Agent Harness: Why the LLM Is the Smallest Part of Your Agent System](https://www.mongodb.com/company/blog/technical/agent-harness-why-llm-is-smallest-part-of-your-agent-system) — MongoDB  
  Argues that the LLM is the most interchangeable component in an agent system; the real engineering challenge is the surrounding harness — tools, memory, state, and orchestration.

---

## 2. Harness Design & Engineering

How to architect, build, and iteratively improve a harness in practice.

- [Harness engineering for coding agent users](https://martinfowler.com/articles/harness-engineering.html) — Martin Fowler  
  A practitioner's guide to configuring the working environment for coding agents, covering tool selection, project scaffolding, feedback loops, and getting the most out of AI coding assistants.

- [Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/) — OpenAI  
  OpenAI's perspective on designing harnesses for software engineering agents, including how to structure tasks, manage context, and get reliable outputs from Codex in production.

- [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) — Anthropic  
  Harness patterns that keep agents productive and safe over extended runs: structured task decomposition, pause-and-resume patterns, and monitoring strategies.

- [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps) — Anthropic  
  A companion piece on structuring harnesses for multi-step application development, covering how to scope tasks, manage state across sessions, and handle errors gracefully.

- [Continually improving our agent harness](https://cursor.com/blog/continually-improving-agent-harness) — Cursor  
  Cursor's iterative approach to improving their coding agent harness, with production lessons on reliability, latency, and how to guide agent behavior without overfitting prompts.

---

## 3. Orchestration & Multi-Agent Patterns

Supervisor patterns, sub-agent delegation, and coordinating fleets of agents toward a shared goal.

- [An open-source spec for Codex orchestration: Symphony](https://openai.com/index/open-source-codex-orchestration-symphony/) — OpenAI  
  Introduces Symphony, OpenAI's open-source specification for orchestrating multi-agent Codex workflows, enabling structured coordination between multiple coding agents.

- [Where to use sub-agents versus agents as tools](https://cloud.google.com/blog/topics/developers-practitioners/where-to-use-sub-agents-versus-agents-as-tools/) — Google Cloud  
  A decision framework for choosing between hierarchical sub-agent delegation (one agent directing another) and tool-based delegation (calling agents as functions), with trade-offs for each.

- [LangGraph Supervisor](https://github.com/langchain-ai/langgraph-supervisor-py) — GitHub  
  A LangGraph library implementing the supervisor multi-agent pattern, where a central orchestrator dynamically routes tasks to specialized worker agents.

- [Developer's guide to multi-agent patterns in ADK](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/) — Google  
  Google's official guide to implementing multi-agent patterns — including parallel execution, sequential pipelines, and dynamic routing — using the Agent Developer Kit.

- [Harrison Chase on deep agents, async sub-agents, and agent identity](https://www.youtube.com/watch?v=c-fsL0gsmo0) — NVIDIA AI Podcast  
  A conversation with LangChain's Harrison Chase on the emerging concept of "deep agents" — long-horizon, async, and identifiable agents — and what that means for harness and infrastructure design.

- [Deep Agents](https://blog.langchain.com/) — LangChain  
  LangChain's exploration of agents that execute complex, long-horizon tasks through extended planning cycles, sub-agent delegation, and iterative refinement rather than single-shot responses.

- [Scaling Managed Agents: Decoupling the brain from the harness](https://www.anthropic.com/engineering/managed-agents) — Anthropic  
  Introduces an architectural pattern that separates the LLM reasoning layer from the execution harness, enabling each to be scaled, updated, and monitored independently.

- [The Multi-Agent Architecture That Actually Ships](https://www.youtube.com/watch?v=ow1we5PzK-o) — Luke Alvoeiro, Factory  
  A practitioner talk on the real-world multi-agent architecture used at Factory, covering what actually works in production versus what sounds good in architecture diagrams.

---

## 4. Long-Running & Durable Execution

Patterns for agents that run for minutes or hours: checkpointing, resumability, and context compaction.

- [Long-running Agents](https://addyo.substack.com/p/long-running-agents) — Addy Osmani  
  Explores the unique challenges of agents that execute over extended periods — context window management, failure recovery, checkpointing, and maintaining coherence on long task horizons.

- [AI Agent Workflow Checkpointing and Resumability](https://zylos.ai/research/2026-03-04-ai-agent-workflow-checkpointing-resumability) — Zylos Research  
  A technical deep dive into strategies for snapshotting agent state so that interrupted or failed workflows can resume rather than restart from scratch.

- [Durable Execution](https://docs.langchain.com/oss/python/langgraph/durable-execution) — LangChain docs  
  LangGraph's durable execution primitives that allow agent workflows to persist across failures and system restarts, enabling fault-tolerant long-running agents.

- [Shell + Skills + Compaction: Tips for long-running agents](https://developers.openai.com/blog/skills-shell-tips) — OpenAI Developers  
  Practical guidance on keeping agents effective over long runs: shell-based task execution, modular skill libraries, and context compaction to manage the growing cost of multi-step workflows.

- [Run long horizon tasks with Codex](https://developers.openai.com/blog/run-long-horizon-tasks-with-codex) — OpenAI Developers  
  A guide to structuring tasks so Codex can execute reliably over extended sequences of steps, including how to decompose goals, handle failures, and verify progress.

---

## 5. Memory & Context Engineering

Managing what agents remember across interactions and what they see in their context window.

- [Memory tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool) — Claude API Docs  
  API documentation for Claude's built-in memory tool, which lets agents persist and retrieve information across interactions using structured key-value storage.

- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — Anthropic  
  Anthropic's engineering perspective on what belongs in an agent's context window and what doesn't, with practical strategies for keeping context relevant, compact, and high-signal.

- [Using agent memory](https://platform.claude.com/docs/en/managed-agents/memory) — Claude API Docs  
  Documentation on Anthropic's managed memory APIs — how agents can store, retrieve, and reason over persistent memories using the Claude SDK's built-in memory capabilities.

---

## 6. Self-Evolving & Adaptive Agents

Agents that improve their own capabilities over time through reflection, memory consolidation, and goal revision.

- [A Survey of Self-Evolving Agents](https://arxiv.org/html/2507.21046v3) — arXiv 2507.21046  
  A comprehensive academic survey categorizing the mechanisms by which agents modify their own capabilities, behaviors, and goals — including tool learning, memory consolidation, and objective refinement.

- [SAGE: Self-evolving Agents with Reflective and Memory-augmented Abilities](https://arxiv.org/html/2409.00872v2) — arXiv 2409.00872  
  Presents SAGE, an agent architecture that uses structured reflection and persistent memory to iteratively improve task performance without human intervention.

- [Hermes Agent: Self-Improving AI with Persistent Memory](https://yuv.ai/blog/hermes-agent) — YUV.AI  
  A practical write-up on building Hermes, a self-improving agent that accumulates and applies lessons from prior interactions through a persistent, evolving memory store.

---

## 7. Case Studies

Real-world engineering reports on deploying agents for complex, long-running tasks.

- [Long-running Claude for scientific computing](https://www.anthropic.com/research/long-running-Claude) — Anthropic  
  A research case study on using Claude for extended scientific computing tasks, with lessons on task framing, output verification, and managing agent autonomy over long horizons.

- [Building a C compiler with a team of parallel Claudes](https://www.anthropic.com/engineering/building-c-compiler) — Anthropic  
  An engineering report on coordinating multiple Claude instances working in parallel to build a C compiler, with insights into task decomposition, synchronization, and quality control.

---

## 8. Tooling, SDKs & Reference

APIs, framework docs, and curated resource lists for building and studying harnesses.

- [awesome-harness-engineering](https://github.com/ai-boost/awesome-harness-engineering) — GitHub  
  A community-curated list of papers, tools, frameworks, and articles on agent harness engineering, organized by topic.

- [Create custom subagents](https://code.claude.com/docs/en/sub-agents) — Claude Code Docs  
  Official Claude Code documentation on defining, configuring, and deploying custom subagent types to handle specialized tasks within a larger Claude Code workflow.

- [Subagents in the SDK](https://platform.claude.com/docs/en/agent-sdk/subagents) — Claude API Docs  
  API reference for creating and coordinating subagents programmatically using Anthropic's agent SDK, including communication patterns and lifecycle management.
