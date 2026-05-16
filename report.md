# Agent Harness Engineering: Challenges, Solutions, and Best Practices

*A synthesis of 32 practitioner articles, engineering blogs, and research papers — as of mid-2026.*

---

## Table of Contents

- [Executive Summary](#executive-summary)
- [Part I — What Is an Agent Harness?](#part-i--what-is-an-agent-harness)
- [Part II — The Core Challenges](#part-ii--the-core-challenges)
  - [1. Context Window Limits and Context Rot](#1-context-window-limits-and-context-rot)
  - [2. Statelessness and the Shift Problem](#2-statelessness-and-the-shift-problem)
  - [3. Durability and Failure Recovery](#3-durability-and-failure-recovery)
  - [4. Long-Running Execution Without Verification](#4-long-running-execution-without-verification)
  - [5. Multi-Agent Coordination Complexity](#5-multi-agent-coordination-complexity)
  - [6. Tool Proliferation and Tool Failure](#6-tool-proliferation-and-tool-failure)
  - [7. Security and Governance](#7-security-and-governance)
  - [8. Observability Gaps](#8-observability-gaps)
  - [9. The Scaling Gap: Stage 2 to Stage 3](#9-the-scaling-gap-stage-2-to-stage-3)
  - [10. Self-Improvement Without Safety Guarantees](#10-self-improvement-without-safety-guarantees)
- [Part III — The Converging Solutions](#part-iii--the-converging-solutions)
  - [Solution 1: The Brain / Hands / Session Split](#solution-1-the-brain--hands--session-split)
  - [Solution 2: Structured State Files as External Memory](#solution-2-structured-state-files-as-external-memory)
  - [Solution 3: Context Compaction and Dynamic Retrieval](#solution-3-context-compaction-and-dynamic-retrieval)
  - [Solution 4: Durable Execution Primitives](#solution-4-durable-execution-primitives)
  - [Solution 5: Generator / Critic Separation](#solution-5-generator--critic-separation)
  - [Solution 6: Minimal, Specialized Tool Sets](#solution-6-minimal-specialized-tool-sets)
  - [Solution 7: Multi-Agent Patterns for Parallelism](#solution-7-multi-agent-patterns-for-parallelism)
  - [Solution 8: Model-Specific Harness Customization](#solution-8-model-specific-harness-customization)
  - [Solution 9: Dual Measurement — Offline + Online](#solution-9-dual-measurement--offline--online)
- [Part IV — Best Practices](#part-iv--best-practices)
  - [1. Externalize all task-critical state](#1-externalize-all-task-critical-state)
  - [2. Decouple brain from hands from session](#2-decouple-brain-from-hands-from-session)
  - [3. Never let agents grade their own work](#3-never-let-agents-grade-their-own-work)
  - [4. Minimize and specialize tool sets](#4-minimize-and-specialize-tool-sets)
  - [5. Design context management as an engineering discipline](#5-design-context-management-as-an-engineering-discipline)
  - [6. Decouple the harness from model assumptions](#6-decouple-the-harness-from-model-assumptions)
  - [7. Specialize agents; resist the generalist reflex](#7-specialize-agents-resist-the-generalist-reflex)
  - [8. Use tools for stateless work; sub-agents for stateful work](#8-use-tools-for-stateless-work-sub-agents-for-stateful-work)
  - [9. Implement security as a harness concern, not a prompt concern](#9-implement-security-as-a-harness-concern-not-a-prompt-concern)
  - [10. Instrument decisions, not just executions](#10-instrument-decisions-not-just-executions)
  - [11. Stack incremental improvements; avoid big-bang rewrites](#11-stack-incremental-improvements-avoid-big-bang-rewrites)
  - [12. Treat self-evolving capabilities as a separate engineering concern](#12-treat-self-evolving-capabilities-as-a-separate-engineering-concern)
- [Part V — Open Problems](#part-v--open-problems)
- [Sources](#sources)

---

## Executive Summary

An agent harness is the software infrastructure surrounding an AI model that handles everything except the model's own reasoning: tool execution, state persistence, memory management, orchestration, verification, and security. The central insight shared across this literature is that **the LLM is the smallest and most interchangeable part of a production agent system.**

[MongoDB's engineering team](https://www.mongodb.com/company/blog/technical/agent-harness-why-llm-is-smallest-part-of-your-agent-system) found that the ratio of harness code to model-interaction code runs roughly 50:1 in governed enterprise deployments. Princeton's CORE-Bench demonstrated the same model scoring 42% under one scaffold and 78% under another. Vercel reduced its agent harness tool count by 80% and watched success rate jump from 80% to 100% while halving tokens and cutting latency from 724 seconds to 141 seconds — without changing the model at all. LangChain moved a coding agent from the bottom to the Top 5 on Terminal Bench 2.0 (52.8% → 66.5%) through harness changes alone. (All figures from [MongoDB](https://www.mongodb.com/company/blog/technical/agent-harness-why-llm-is-smallest-part-of-your-agent-system).)

The challenges are well-understood. The solutions are largely converging. The gap is execution.

---

## Part I — What Is an Agent Harness?

A harness is the complete architectural system surrounding an LLM that manages the lifecycle of a task: from intent capture through planning, tool execution, verification, and persistence ([Firecrawl](https://www.firecrawl.dev/blog/what-is-an-agent-harness)). [LangChain's anatomy](https://www.langchain.com/blog/the-anatomy-of-an-agent-harness) defines it as "every piece of code, configuration, and execution logic that isn't the model itself."

The minimum viable harness has three responsibilities:

1. **Tool integration** — exposing callable functions (file I/O, code execution, web access, APIs) with validated inputs and sanitized returns
2. **State management** — maintaining context across tool calls and across sessions
3. **Verification** — confirming that outputs meet success criteria before marking work done

Without these, agents fail in predictable ways: they exhaust context mid-task, hallucinate tool calls, declare premature completion, or lose all progress to a single network failure ([Firecrawl](https://www.firecrawl.dev/blog/what-is-an-agent-harness)).

---

## Part II — The Core Challenges

### 1. Context Window Limits and Context Rot

The transformer's n² attention relationship means quality degrades as context grows — not linearly, but systematically. [Anthropic's context engineering team](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) calls this *context rot*: accumulated tool outputs, error messages, and intermediate results crowd out the original instructions and compress the model's effective working memory.

Two failure modes are well-documented:

- **Context anxiety**: Models wrap up work prematurely as they approach window limits, producing plausible-looking but incomplete output. [Anthropic's harness design paper](https://www.anthropic.com/engineering/harness-design-long-running-apps) describes models "responding by confidently wrapping up — even when the task is obviously incomplete."
- **Lost in the Middle**: Critical information buried in the middle of a long context receives disproportionately less attention than content at the prompt boundaries ([Anthropic context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)).

Both [LangChain](https://www.langchain.com/blog/the-anatomy-of-an-agent-harness) and [Addy Osmani](https://addyo.substack.com/p/long-running-agents) identify this as the primary bottleneck for long-horizon work: "even million-token windows eventually fill up, and context degradation occurs well before capacity limits."

### 2. Statelessness and the Shift Problem

LLMs have no memory between sessions. [Addy Osmani](https://addyo.substack.com/p/long-running-agents) frames it as an organizational problem: "imagine a software project staffed by engineers working in shifts, where each new engineer arrives with no memory of what happened on the previous shift." Each session begins with zero knowledge of previous work, git history, failed approaches, or partial completions.

The consequences compound: agents either restart from scratch (wasting effort) or receive incomplete handoffs and confidently build on broken foundations. [Anthropic's effective harnesses guide](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) documents both failure modes in production.

### 3. Durability and Failure Recovery

Long-running tasks fail. Network interruptions, container crashes, context limits, and model errors are not edge cases — they are expected events in any multi-hour or multi-day workflow. Without explicit checkpointing, a failure at step 47 of 50 means restarting at step 1.

[Anthropic's managed agents team](https://www.anthropic.com/engineering/managed-agents) experienced this directly: early architectures coupling sessions, harnesses, and sandboxes into single containers turned every failure into a total loss. As they describe it, these were "pets" — any one dying was a crisis. [LangGraph's durable execution documentation](https://docs.langchain.com/oss/python/langgraph/durable-execution) formalizes the requirement: non-deterministic operations (API calls, file writes, random generation) must be isolated into tasks that can be checkpointed and replayed without re-executing completed side effects.

### 4. Long-Running Execution Without Verification

Models systematically over-report task completion. When asked to evaluate their own work, they "respond by confidently praising it — even when, to a human observer, the quality is obviously mediocre" ([Anthropic harness design](https://www.anthropic.com/engineering/harness-design-long-running-apps)). [Anthropic's scientific computing case study](https://www.anthropic.com/research/long-running-Claude) found the same: without external verification loops, agents declared success at intermediate states and stopped.

This is not a prompt engineering problem. It is a structural problem: the entity generating outputs cannot reliably evaluate them. Self-evaluation bias is inherent.

### 5. Multi-Agent Coordination Complexity

Parallel agents introduce synchronization hazards that single-agent systems never face. [Anthropic's C compiler project](https://www.anthropic.com/engineering/building-c-compiler) found that 16 agents working simultaneously on shared code created merge conflicts and task duplication. When the project shifted to debugging the Linux kernel — a sequential problem — all agents hit identical bugs simultaneously, providing no benefit from parallelism.

Coordination patterns must handle task locking, context isolation vs. sharing, and result synthesis. [Google's ADK guide](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/) and the [Google Cloud sub-agents guide](https://cloud.google.com/blog/topics/developers-practitioners/where-to-use-sub-agents-versus-agents-as-tools/) both address the fundamental design tension between shared and isolated context.

### 6. Tool Proliferation and Tool Failure

Tool sets grow. Engineers add tools for new capabilities without removing old ones. [Cursor's production experience](https://cursor.com/blog/continually-improving-agent-harness) identified "tool errors creating context rot" as a primary reliability problem: each failed tool call leaves an error trace in context that subtly degrades all subsequent decisions. Their systematic classification of error types and a focused sprint reduced unexpected tool errors by an order of magnitude.

[OpenAI's long-running agent tips](https://developers.openai.com/blog/skills-shell-tips) identify the same failure mode: when skill descriptions are written as marketing copy rather than routing logic, misfires are frequent. Glean found that adding "don't use when" guidance alongside positive examples reduced skill triggering errors by 20%. [Anthropic's context engineering paper](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) puts it plainly: "if engineers cannot definitively identify which tool applies in a scenario, agents cannot either."

### 7. Security and Governance

Security is where most enterprise agent projects stall before production ([MongoDB](https://www.mongodb.com/company/blog/technical/agent-harness-why-llm-is-smallest-part-of-your-agent-system)). The harness must handle identity propagation, permission scoping, audit trails, and prompt injection defense. [OpenAI's skill guidance](https://developers.openai.com/blog/skills-shell-tips) is explicit: "skills combined with open network access create high-risk data exfiltration paths; use strict allowlists and avoid open internet in consumer-facing flows."

### 8. Observability Gaps

Agent observability is fundamentally different from application observability. [MongoDB's analysis](https://www.mongodb.com/company/blog/technical/agent-harness-why-llm-is-smallest-part-of-your-agent-system) identifies three signals that application monitoring tools don't capture: what the agent decided (not just what it did), why it chose that path (which memory and tool calls contributed), and whether the decision was correct (evaluation, not just execution). As of early 2026, no widely adopted AgentOps standard exists.

### 9. The Scaling Gap: Stage 2 to Stage 3

[MongoDB's maturity model](https://www.mongodb.com/company/blog/technical/agent-harness-why-llm-is-smallest-part-of-your-agent-system) is the most rigorous framing of where teams actually fail. Most teams building agents are at Stage 2 (stateful orchestration: context delivery, memory architecture, multi-step tasks) but believe they are at Stage 3 (governed fleet: durable execution, identity propagation, automatic cost/audit). The real production failures cluster at this transition: cost attribution at per-agent granularity, automatic evaluation on every change, fleet-wide observability, and security compliance. These are platform problems that require a separate engineering investment from the harness itself.

### 10. Self-Improvement Without Safety Guarantees

[The arXiv survey of self-evolving agents](https://arxiv.org/html/2507.21046v3) identifies that agents capable of autonomous tool generation risk "creating tools with exploitable vulnerabilities or unintended harmful behaviors." Catastrophic forgetting — losing old capabilities while acquiring new ones — remains unsolved. Current evaluation benchmarks do not capture adaptive capabilities across diverse task distributions.

---

## Part III — The Converging Solutions

### Solution 1: The Brain / Hands / Session Split

The most significant architectural convergence across [Anthropic](https://www.anthropic.com/engineering/managed-agents), [OpenAI](https://developers.openai.com/blog/skills-shell-tips), and [LangChain](https://addyo.substack.com/p/long-running-agents) is decoupling the reasoning loop from the execution environment from the durable session log:

- **Brain**: The model and its reasoning loop (stateless, replaceable)
- **Hands**: Ephemeral sandboxed execution environments ("cattle, not pets")
- **Session**: An append-only event log of all thoughts, tool calls, and observations (lives outside context windows, queryable)

[Anthropic's managed agents architecture](https://www.anthropic.com/engineering/managed-agents) describes how this eliminates the "pet infrastructure" problem: containers become callable resources (`execute(name, input) → string`) that fail cleanly with retriable tool-call errors rather than crashing the whole session.

### Solution 2: Structured State Files as External Memory

Across the practitioner literature — [Anthropic's scientific computing case study](https://www.anthropic.com/research/long-running-Claude), [the C compiler project](https://www.anthropic.com/engineering/building-c-compiler), [Addy Osmani's long-running agents guide](https://addyo.substack.com/p/long-running-agents), [OpenAI's Codex long-horizon tips](https://developers.openai.com/blog/run-long-horizon-tasks-with-codex) — a consistent pattern emerges: **all task-critical information must live outside the context window in structured files.**

The canonical implementation:
- `CLAUDE.md` or `AGENT_PROMPT.md`: master plan, editable by the agent as understanding evolves
- `PROGRESS.md` or equivalent JSON: current status, completed steps, failed approaches with explanations
- Git commits as structured checkpoints with descriptive messages functioning as "lab notes"

The Ralph Loop operationalizes this ([Anthropic scientific computing](https://www.anthropic.com/research/long-running-Claude)): a simple bash script loops through tasks while maintaining state in JSON files, re-prompting the agent in clean context windows with the current state file as its only history.

### Solution 3: Context Compaction and Dynamic Retrieval

[Anthropic's context engineering paper](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) provides the clearest framework for managing context as a scarce resource:

- **Compaction**: Summarize conversation history at intervals, preserving architectural decisions and unresolved issues, discarding redundant outputs and completed steps
- **"Just in time" retrieval**: Agents use tools to dynamically load relevant data at runtime rather than pre-loading everything upfront
- **Progressive disclosure**: Tools and context loaded incrementally as the task demands them
- **Goldilocks prompting**: System prompts at "the minimal set of information that fully outlines expected behavior" — canonical examples, not exhaustive rules

[LangChain's anatomy](https://www.langchain.com/blog/the-anatomy-of-an-agent-harness) identifies the "Ralph Loop" as the simplest practitioner implementation: a bash script looping tasks while maintaining state in JSON files and progress logs, proving sophisticated harnesses matter more than model capability for extended work.

### Solution 4: Durable Execution Primitives

[LangGraph's durable execution](https://docs.langchain.com/oss/python/langgraph/durable-execution) formalizes checkpoint-and-resume as a first-class primitive with three modes:
- `"exit"`: checkpoint only at completion (best performance)
- `"async"`: asynchronous checkpointing between steps (balanced)
- `"sync"`: synchronous checkpointing before each step (maximum safety)

The non-determinism principle is critical: any operation with side effects (API calls, file writes, randomness) must be wrapped in a task node so the system can replay execution from a checkpoint without re-executing completed side effects.

### Solution 5: Generator / Critic Separation

Structural verification, not self-evaluation. The generator/critic pattern (called "planner/generator/evaluator" in [Anthropic's harness design paper](https://www.anthropic.com/engineering/harness-design-long-running-apps), "generator and critic" in [Google's ADK guide](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/)) separates generation from evaluation as distinct structural roles. Anthropic found that even aesthetic judgments work better with explicit criteria graded by a separate evaluator than with self-assessment.

The [Ralph Loop](https://www.anthropic.com/research/long-running-Claude) applies the same principle at the session level: an outer loop re-prompts agents that claim completion with "is it really done?" until criteria are demonstrably met. Browser automation via Playwright or Puppeteer, as recommended in [Anthropic's harness design paper](https://www.anthropic.com/engineering/harness-design-long-running-apps), provides the most rigorous form of verification by simulating real user interactions rather than inspecting code structure.

### Solution 6: Minimal, Specialized Tool Sets

The Vercel finding, cited in [MongoDB's analysis](https://www.mongodb.com/company/blog/technical/agent-harness-why-llm-is-smallest-part-of-your-agent-system), is the strongest empirical evidence in this literature: removing 80% of tools from their agent harness — without changing the model — produced a 25% success rate improvement, 50% token reduction, and 80% latency reduction.

The design principles from [Anthropic's context engineering guide](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) and [OpenAI's skill tips](https://developers.openai.com/blog/skills-shell-tips):
- Tools should be self-contained and unambiguous
- Tool descriptions are routing logic, not marketing copy — include when *not* to use each tool
- Negative examples reduce misfires more than additional positive examples (Glean's 20% improvement)
- If two engineers disagree on which tool applies to a scenario, agents will too

### Solution 7: Multi-Agent Patterns for Parallelism

[Google ADK's eight patterns](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/) cover the main coordination strategies:

| Pattern | Best For |
|---|---|
| Sequential pipeline | Tasks with strict ordering dependencies |
| Coordinator / dispatcher | Dynamic routing by intent |
| Parallel fan-out / gather | Independent subtasks, latency reduction |
| Hierarchical decomposition | Tasks exceeding single context window |
| Generator / critic | Quality assurance and validation |
| Human-in-the-loop | High-stakes, irreversible actions |

For parallel coding agents specifically, [Anthropic's C compiler project](https://www.anthropic.com/engineering/building-c-compiler) found two critical patterns:
- **Task locking via files**: agents claim tasks by writing lock files, preventing duplicate work
- **Oracle patterns**: a known-good reference implementation (e.g., GCC) enables agents to debug different code subsets in parallel without stepping on each other

The [LangGraph Supervisor](https://github.com/langchain-ai/langgraph-supervisor-py) provides a reference implementation of the coordinator/dispatcher pattern. The [Google Cloud sub-agents guide](https://cloud.google.com/blog/topics/developers-practitioners/where-to-use-sub-agents-versus-agents-as-tools/) and [Google ADK guide](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/) both recommend beginning with simple sequential chains before adding parallelism.

### Solution 8: Model-Specific Harness Customization

[Cursor's experience](https://cursor.com/blog/continually-improving-agent-harness) surfaces a practical point that abstract architecture discussions miss: different model providers have different native formats. OpenAI models are trained on patch-based file edits; Anthropic models on string replacement. Applying one model's expected format to another produces systematic errors that look like model failures but are actually harness mismatches. Model-specific harnesses — customized prompts, tool formats, and instruction styles — consistently outperform one-size-fits-all approaches.

### Solution 9: Dual Measurement — Offline + Online

[Cursor's measurement framework](https://cursor.com/blog/continually-improving-agent-harness) is the most complete in this literature:
- **Offline**: internal benchmarks (CursorBench) run against fixed test cases, catching regressions before deployment
- **Online**: A/B testing with real users, measuring "Keep Rate" (code that remains in the codebase after a fixed interval) and LLM-assessed satisfaction signals
- **Automated error detection**: weekly automations surface newly spiked error categories and create investigation tickets

Pass rate on test cases is necessary but insufficient. Keep Rate measures whether the agent's work was actually useful in production — a much harder and more honest signal.

---

## Part IV — Best Practices

The following practices are distilled from convergence across the full set of sources.

---

### 1. Externalize all task-critical state

Never trust the context window as your only record of progress. Every meaningful state transition — completed steps, failed approaches, current plan, known issues — must be written to durable external storage before the task continues. Use structured formats (JSON, markdown with defined sections) that the agent can read and update programmatically. Git commits are free checkpoints.

*Convergence: [Anthropic scientific computing](https://www.anthropic.com/research/long-running-Claude), [C compiler project](https://www.anthropic.com/engineering/building-c-compiler), [Addy Osmani](https://addyo.substack.com/p/long-running-agents), [OpenAI Codex long-horizon](https://developers.openai.com/blog/run-long-horizon-tasks-with-codex).*

---

### 2. Decouple brain from hands from session

Design harnesses so that the reasoning loop, the execution environment, and the session record are independently replaceable. A container failure should trigger a retriable tool-call error, not a session loss. Sessions should be queryable event logs that outlive any individual component.

*Source: [Anthropic managed agents architecture](https://www.anthropic.com/engineering/managed-agents).*

---

### 3. Never let agents grade their own work

Separate generation from evaluation structurally. Evaluators should have explicit, measurable success criteria. Use browser automation or integration tests as ground truth. Apply the Ralph Loop for tasks where agents are prone to premature completion claims.

*Convergence: [Anthropic harness design](https://www.anthropic.com/engineering/harness-design-long-running-apps), [scientific computing case study](https://www.anthropic.com/research/long-running-Claude), [Google ADK generator/critic pattern](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/).*

---

### 4. Minimize and specialize tool sets

More tools reliably decreases performance. Audit tool sets regularly; remove tools that duplicate existing capabilities. Write tool descriptions as routing logic with explicit "do not use when" guidance. If you cannot definitively identify which tool applies to a scenario, neither can the agent.

*Evidence: [Vercel/MongoDB study](https://www.mongodb.com/company/blog/technical/agent-harness-why-llm-is-smallest-part-of-your-agent-system), [Cursor error reduction sprint](https://cursor.com/blog/continually-improving-agent-harness), [OpenAI skill best practices](https://developers.openai.com/blog/skills-shell-tips), [Anthropic context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents).*

---

### 5. Design context management as an engineering discipline

Do not treat context window limits as an exceptional condition. Plan for compaction from the start. Use "just in time" retrieval rather than front-loading. Organize system prompts with XML tags or markdown headers. Curate canonical examples instead of exhaustive rule lists.

*Source: [Anthropic context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents), [LangChain anatomy](https://www.langchain.com/blog/the-anatomy-of-an-agent-harness), [Cursor](https://cursor.com/blog/continually-improving-agent-harness).*

---

### 6. Decouple the harness from model assumptions

Model capabilities improve continuously; harness assumptions about model limits become stale. [Anthropic's managed agents team](https://www.anthropic.com/engineering/managed-agents) found that context anxiety workarounds built for earlier models became unnecessary overhead with newer versions. Architect for model upgrade: create interfaces unopinionated about which model fills the brain role.

---

### 7. Specialize agents; resist the generalist reflex

The practitioner evidence is consistent: specialized agents outperform generalists on complex, multi-domain tasks. The [C compiler project](https://www.anthropic.com/engineering/building-c-compiler), [Anthropic's harness design paper](https://www.anthropic.com/engineering/harness-design-long-running-apps)'s three-agent architecture, and [LangGraph Supervisor](https://github.com/langchain-ai/langgraph-supervisor-py) all demonstrate that routing distinct problem types to distinct agents produces more reliable results than a single generalist agent.

---

### 8. Use tools for stateless work; sub-agents for stateful work

[The Google Cloud decision framework](https://cloud.google.com/blog/topics/developers-practitioners/where-to-use-sub-agents-versus-agents-as-tools/) is the clearest articulation of a frequently confused distinction. Agents-as-tools work for discrete, reusable, isolated functions. Sub-agents work for complex, stateful processes that require access to conversational history and multi-step reasoning. Using tools for stateful tasks creates massive overhead from repeatedly passing full state context; using sub-agents for stateless tasks introduces unnecessary coupling and latency.

---

### 9. Implement security as a harness concern, not a prompt concern

Prompt-based security is insufficient. Security belongs in the harness: strict network allowlists, credential injection via `domain_secrets` rather than model context ([OpenAI](https://developers.openai.com/blog/skills-shell-tips)), sandbox isolation with configurable access controls, and identity propagation that produces audit evidence automatically ([MongoDB](https://www.mongodb.com/company/blog/technical/agent-harness-why-llm-is-smallest-part-of-your-agent-system)). Build these before production; retrofitting is far more expensive.

---

### 10. Instrument decisions, not just executions

Standard application monitoring (latency, error rate) is necessary but insufficient for agents. Add traces that capture: what the agent decided, which memory and tool calls contributed to that decision, and whether the decision was correct. Implement offline benchmarks for regression detection and online metrics (Keep Rate or equivalent) for production quality measurement.

*Source: [MongoDB observability analysis](https://www.mongodb.com/company/blog/technical/agent-harness-why-llm-is-smallest-part-of-your-agent-system), [Cursor dual measurement approach](https://cursor.com/blog/continually-improving-agent-harness).*

---

### 11. Stack incremental improvements; avoid big-bang rewrites

[Cursor's finding](https://cursor.com/blog/continually-improving-agent-harness) is backed by their production data: most harness improvements come from systematically stacking small refinements — better tool descriptions, model-specific formatting, error classification sprints — rather than architectural overhauls. Instrument before you iterate. Measure each change with offline evals before deployment.

---

### 12. Treat self-evolving capabilities as a separate engineering concern

Self-improvement mechanisms (memory consolidation, autonomous skill generation, reflective loops) require separate safety and evaluation infrastructure that most harnesses do not have. [The arXiv survey](https://arxiv.org/html/2507.21046v3) identifies catastrophic forgetting, exploitable tool generation, and evaluation gaps as unsolved problems. [SAGE](https://arxiv.org/html/2409.00872v2) and [Hermes](https://yuv.ai/blog/hermes-agent) demonstrate working implementations; both confine evolution to memory and skill accumulation rather than full objective modification.

---

## Part V — Open Problems

Despite the convergence on patterns, several problems remain without settled solutions as of mid-2026:

**AgentOps standardization.** No widely adopted observability standard for agents exists ([MongoDB](https://www.mongodb.com/company/blog/technical/agent-harness-why-llm-is-smallest-part-of-your-agent-system)). Teams instrument ad hoc, making cross-team comparison and industry benchmarking difficult.

**Long-term memory at scale.** Vector-indexed episodic memory works for single sessions; quality degrades at scale across thousands of sessions, across organizational boundaries, and across model upgrades that change embedding behavior ([arXiv survey](https://arxiv.org/html/2507.21046v3)).

**Evaluation for non-deterministic systems.** Deterministic success criteria don't map cleanly onto non-deterministic agents. Keep Rate and LLM-assessed satisfaction are proxies, not ground truth ([Cursor](https://cursor.com/blog/continually-improving-agent-harness), [MongoDB](https://www.mongodb.com/company/blog/technical/agent-harness-why-llm-is-smallest-part-of-your-agent-system)).

**Self-improvement safety.** Autonomous tool generation and objective refinement create attack surfaces that current sandboxing approaches do not fully close ([arXiv survey](https://arxiv.org/html/2507.21046v3)).

**The Stage 2 → Stage 3 transition.** Most teams are building Stage 2 harnesses (stateful, single-team, working). The platform requirements for Stage 3 (durable execution, identity propagation, automatic cost/audit, fleet-wide observability) require a separate engineering investment that the agent harness cannot absorb ([MongoDB](https://www.mongodb.com/company/blog/technical/agent-harness-why-llm-is-smallest-part-of-your-agent-system)).

---

## Sources

This report synthesizes the 32 sources listed in [`sources.md`](sources.md). The grouping and full source list with summaries is in [`README.md`](README.md).
