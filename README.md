# Tencent AI Cloud Hackathon

## The Digital Native Track — Ryde

**Challenge: Multi-Agent Autonomous Dispute Resolution System**

## 1. Track Overview

The Digital Native Track features real-world business challenges contributed by Ryde, a Singapore-headquartered ride-hailing and carpooling platform.

Participants will use AI technologies to develop practical, impactful solutions for the mobility and digital services sector.

### Participation Requirements

- This track presents one real-world enterprise challenge statement.
- Each team must select one case study to solve.
- Clearly indicate your chosen case study at the beginning of your presentation.

## 2. Background

Ride-hailing companies process thousands of dispute tickets daily, ranging from fare disputes and route deviations to property damage, safety incidents, and no-show charges.

These disputes are often complex, subjective, and emotionally charged. Human support agents must manually review GPS telemetry, chat logs, photos, payment records, and company policies before reaching a decision.

This approach creates several challenges:

| Challenge | Impact |
| --- | --- |
| High operational costs | Millions spent annually on human support hours. |
| Slow resolution times | Disputes typically take 24–72 hours to resolve. |
| Inconsistent rulings | Different agents may reach different conclusions on similar cases. |
| User churn | Customers who feel unfairly treated may leave the platform. |

## 3. Problem Statement

Build an autonomous, multi-agent dispute resolution system that handles complex conflicts between riders and drivers.

The system should gather evidence, build cases, apply company policy, and issue fair rulings quickly and transparently, without human intervention for the majority of standard dispute categories.

## 4. Required MVP: Core Agents

Teams must implement three core agents that operate on text-based and structured evidence, such as GPS coordinates, chat logs, fare breakdowns, and timestamps.

| Agent | Role | Required Capabilities |
| --- | --- | --- |
| Rider Advocate Agent | Represents the rider’s perspective. | Gathers rider-side evidence, articulates the rider’s claim using company policy, and argues for rider-favourable outcomes. |
| Driver Advocate Agent | Represents the driver’s perspective. | Gathers driver-side evidence, builds the driver’s defence using company policy, and argues for driver-favourable outcomes. |
| Judge Agent | Acts as an impartial arbitrator. | Weighs both cases, applies company policy, issues a ruling, and explains its reasoning in natural language. Possible outcomes include refunds, compensation, or no action. |

### MVP Evidence Sources

| Evidence Source | Areas of Analysis |
| --- | --- |
| GPS and telemetry data | Actual versus optimal route, unexpected stops, and actual versus estimated trip duration. |
| Chat and communication logs | Sentiment, agreements, disagreements, and threats. |
| Payment and fare data | Fare breakdowns, surge pricing disputes, and promo code usage. |
| Historical behaviour profiles | Rider and driver dispute histories, rating patterns, and account age. |

### MVP Workflow

1. **Dispute submission:** A rider or driver files a dispute. Example: “The driver took a longer route and I was overcharged.”
2. **Evidence gathering:** The Rider Advocate Agent and Driver Advocate Agent autonomously gather evidence from the available data sources.
3. **Case presentation:** Each advocate presents its case, citing relevant company policies.
4. **Review and ruling:** The Judge Agent reviews both cases, applies policy, and issues a ruling with a confidence score and a natural-language reasoning summary.
5. **Outcome communication:** The system provides both parties with the ruling, recommended action, and explanation. Example: A partial refund of $3.25.

## 5. Optional Stretch Goals

These enhancements are intended for teams that have completed a fully functional MVP. They earn bonus points and demonstrate deeper technical capability.

| Agent or Capability | Function | Added Technical Complexity |
| --- | --- | --- |
| Evidence Collection Agent | Coordinates multimodal evidence retrieval across tools and APIs, then provides structured evidence to the advocate agents. | Tool use, API integration, and orchestration. |
| Fraud and Bad-Faith Detection Agent | Runs in parallel to detect dispute abuse, fake claims, or collusion, and provides risk signals to the Judge Agent. | Behavioral modelling and risk scoring. |
| Policy and Precedent Agent | Maintains a dynamic knowledge base of company policies and past rulings, providing recommendations for consistent decisions. | Knowledge-base construction and retrieval, such as a RAG architecture. |
| Image Analysis — Multimodal | Assesses mess or damage photos for authenticity, trip-timestamp alignment, and signs of AI generation. | Computer vision and multimodal LLM capabilities. |
| Escalation Protocol | Escalates cases to a human reviewer with a complete case summary when the Judge Agent’s confidence falls below a threshold. | Conditional logic, threshold tuning, and human-in-the-loop design. |
| Learning Feedback Loop | Captures human overrides and feeds corrections into the Policy and Precedent Agent’s knowledge base. | Feedback ingestion and knowledge-base updates. |
| SLA and Routing Manager | Prioritises disputes by urgency and value, fast-tracking high-priority cases such as safety incidents. | Queue management and prioritisation. |

## 6. Strategic Guardrails

### Scope Management

- The required deliverable is the three core agents handling text-based and structured evidence. Evaluation will focus primarily on this.
- Advanced agents, image processing, and multimodal capabilities are stretch goals. Attempt them only after the MVP is fully functional.
- Teams may mock or simulate external APIs and data sources where real APIs are unavailable.
- A sample dataset will be provided.

### Technical Constraints

- Teams may use any LLM or AI agent framework, including LangChain, AutoGen, CrewAI, or a custom implementation.
- By Demo Day, the system must demonstrate a working end-to-end flow for at least two dispute categories, such as route deviation and no-show charges.
- Inter-agent communication must be observable. Judges should be able to see how agents exchange information and build their cases through a visible communication log or user interface.

## 7. Sample Dispute Categories

The system should handle at least two of the following dispute types:

| Dispute Type | Example | Additional Requirement |
| --- | --- | --- |
| Route deviation | “The driver took a longer route and I was overcharged.” | — |
| No-show charge | “The driver didn’t show up, but I was charged a cancellation fee.” | — |
| Property damage or mess | “The rider spilled drinks in the car, and the driver is claiming cleaning fees.” | Requires image analysis; a stretch goal. |
| Safety incident | “The driver behaved inappropriately during the trip.” | — |

## 8. Required Deliverables

| Deliverable | Requirement |
| --- | --- |
| Working prototype | An end-to-end solution capable of handling at least two dispute categories. |
| Architecture diagram | A clear visual representation of the multi-agent system and its key components. |
| Demo walkthrough | A live demonstration showing how a dispute is processed and resolved autonomously. |
| Source code | Complete source code submitted through a GitHub repository. |

> **Note:** The listed features provide guidance. Participants are strongly encouraged to explore alternative approaches that meaningfully address the problem statement.
