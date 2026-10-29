# Cerebral Valley submission draft

Paste into https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit. The form fields were not public when this was written. The blocks below match what the portal is likely to ask for. Cut to fit a length limit if the form has one. Do not add mock-mode detection rates to the form as if they were Prompt Guard or Muse Spark measurements.

## Project name

Kalkan

## Track

Startup

## Organisation

KENOPA LTD

## Designated contact

Erçin, for notices and prize payment on behalf of the startup.

## Tagline

A drop-in firewall that stops indirect prompt injection in tool-using agents, including attacks written in Turkish.

## Description

Kalkan is a proxy that sits in front of a tool-using agent. Before a tool runs, Kalkan does two passes.

Pass 1 screens untrusted text: the email, the document, and the tool arguments. The production screen is Llama Prompt Guard 2 86M. Pass 2 is Muse Spark on Meta Model API, Standard mode (`muse-spark-1.3`), with structured output. The judge sees the user's intent, the policy, the proposed tool, and the pass-1 label, and returns allow, block, or confirm, with the rule that fired and a short explanation. A hard deny still blocks secret reads if the judge is wrong.

The product bet is language. Prompt Guard 2's model card evaluates English, French, German, Hindi, Italian, Portuguese, Spanish, and Thai. Turkish is not on that list. Teams shipping agents in Türkiye, and in other languages outside that card, need a firewall that does not depend on the screen alone. Kalkan's judge blocks a forward the user did not ask for even when the screen misses a paraphrase.

A built-in red team uses Muse Wonder (`muse-wonder-1.0`, Standard mode) as an attacker with two jobs in the plan: an English mutator and a Turkish specialist. It replays injections against a sandbox agent with a fake inbox, documents, and tools, and scores whether the harmful tool was allowed to run. Misses can be exported for a later Prompt Guard fine-tune. This submission does not claim that fine-tune has been run.

The demo is a Turkish invoice. A payment reminder hides an instruction to forward the company's files. Unprotected, the sandbox agent follows it. With Kalkan, the read is allowed, the forward and the send are blocked, and the screen names the rule. A dashboard shows the decision log and held-out stop rates from the eval harness.

Who it is for: any team putting a tool-using model on untrusted mail, documents, or web pages, especially outside the languages their first screen was scored on.

## Meta AI tooling

- Muse Spark 1.3 on Meta Model API, Standard mode, as the intent judge. Chat Completions, JSON schema, actions allow / block / confirm.
- Muse Wonder 1.0 on Meta Model API, Standard mode, as the attacker, prompted to plan with an English mutator and a Turkish specialist.
- Llama Prompt Guard 2 86M as the optional fast screen, behind the same interface as the offline heuristic. Weights are gated and are not redistributed.
- Contributor model IDs are refused. Security content stays on Standard mode, where it is not used for training.

Base URL: `https://api.meta.ai/v1`.

## What the demo video shows

1. A Turkish invoice with a hidden forward instruction. The unprotected sandbox agent leaks.
2. Kalkan blocks the forward and the send, allows the read and the draft, and shows rule `no-instruction-override`.
3. The attacker produces a paraphrase that misses pass 1. Pass 2 still blocks the tool. A session literal catches that exact string on replay. The video says this is not a weight fine-tune.
4. The held-out chart. The spoken numbers are whatever the harness file on screen says, and the video says whether that file is mock mode or live mode.

## Repository

Private git repository. Link to be added by the submitter. Fresh work for this hackathon. Open-source dependencies and their licences are listed in the README. Kalkan's own code is owned by KENOPA LTD.

## Video

Link to be added after the recording. Script: `DEMO.md`. About three minutes.

## Honest limits to keep in the form if there is room

The build runs without a Model API key. Until `META_API_KEY` is set, the judge and the attacker are offline stand-ins, and the dashboard says so. Until the Hugging Face gate for Prompt Guard 2 is accepted, pass 1 is Kalkan's own heuristic, not the 86M model. Held-out rates in the repo today measure that offline pair. They are not Meta's published Prompt Guard figures. A Turkish fine-tune of Prompt Guard has not been trained.

## Do not include

Client data, production prompts, API keys, or findings from other programs.
