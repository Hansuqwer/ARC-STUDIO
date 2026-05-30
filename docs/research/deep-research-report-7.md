# ARC Studio memory, context, and RAG roadmap

## Recommended memory architecture

Based on the ARC capabilities you listed, the right next step is **not** “turn memory on everywhere.” The right next step is to turn ARC’s current prototype into a **local-first memory subsystem with explicit scopes, strong provenance, and injection disabled by default**. That matches the most credible patterns in the market: Letta separates always-in-context memory blocks from archival memory queried on demand; LangGraph/LangMem split thread-scoped persistence from namespaced long-term stores and explicitly distinguish semantic, episodic, and procedural memory; Claude Projects and ChatGPT Projects scope uploaded knowledge and instructions to a project/workspace rather than treating all prior information as one undifferentiated global memory. citeturn27search0turn27search5turn29view1turn29view2turn25view0turn25view1turn26view3

For ARC, I recommend a **three-tier design**:

### Run state

This is the existing deterministic trace plus execution-local state. It should remain the ground truth for what happened in a run. LangGraph’s checkpoint model is useful here: checkpoints give replay, time-travel debugging, and fault recovery, but they are not the same thing as reusable long-term memory. citeturn29view4

### Workspace memory

This should become ARC’s primary memory tier. It is where ARC stores reusable facts, decisions, failures, tool patterns, model/provider notes, and codebase-derived conventions that are specific to one repository or workspace. LangGraph stores long-term memory as JSON documents under namespaces and keys; that namespace model is a strong fit for ARC’s per-workspace boundaries. citeturn29view1

### Cross-workspace sanitised memory

This should exist only as a **derived** tier, never as raw pooled memory. Claude Projects make context reusable only when explicitly added to project knowledge; OpenAI Projects inherit workspace controls and do not create a separate uncontrolled memory plane. ARC should follow that principle and allow cross-workspace reuse only for sanitised, policy-approved patterns such as abstract tool heuristics, high-level decision templates, and model/provider quirks. Raw code, raw paths, raw stack traces, customer identifiers, or ticket text should not cross workspace boundaries by default. citeturn25view1turn26view3

The practical schema I recommend is:

- `runs`, `spans`, `tool_calls`, `artifacts`
- `memory_items`
- `memory_evidence`
- `memory_edges`
- `memory_tombstones`
- `workspace_policies`
- `sanitised_global_patterns`
- `code_chunks`
- `symbols`
- `retrieval_logs`
- `injection_decisions`

Each `memory_item` should carry: `id`, `workspace_id`, `class`, `summary`, `canonical_text`, `source_kind`, `source_run_id`, `source_span_ids`, `source_hashes`, `extractor_version`, `redaction_version`, `created_at`, `last_used_at`, `expiry_policy`, `confidence`, `privacy_label`, `staleness_score`, and `deletion_state`. That is stricter than most consumer memory systems, but it is the minimum needed if ARC wants robust deletion, ranking, and auditability. The broad architecture is also consistent with Letta’s emphasis on explicitly editable memory rather than hidden latent memory, and with LangMem’s background consolidation plus hot-path memory tools. citeturn27search0turn27search5turn29view3

One architectural distinction matters a lot: **codebase indexing should be its own subsystem, not just another memory table**. Cursor, Continue, and Cody all treat code retrieval as a dedicated retrieval problem with indexing, chunking, search, and ranking machinery separate from conversational memory. Cursor uses Merkle trees, syntactic chunks, and cached embeddings; Continue combines embeddings retrieval with keyword search and stores local index metadata in SQLite; Cody uses keyword search, Sourcegraph Search, and code-graph context together. citeturn22view0turn23view0turn22view4turn24view0

The consequence for ARC is straightforward: keep **memory** for “what ARC should remember from experience,” and build **code index** for “what ARC should retrieve from the repository.” Do not collapse those into one data structure.

## Local-first storage options comparison

The strongest default for ARC is a **SQLite-first control plane**, with optional retrieval backends behind an adapter. SQLite already gives reliable local storage, mature SQL, and built-in FTS5; it also now has both third-party and emerging official vector options. At the same time, deletion semantics need care, because SQLite’s FTS shadow tables and WAL/temp files complicate strong erasure guarantees. citeturn8search0turn18search1turn18search2turn18search6turn18search18

| Storage option | Best fit for ARC | Key strengths | Key weaknesses | Recommendation |
|---|---|---|---|---|
| **SQLite + FTS5 + graph tables** | Phase-one default | Single local file, SQL joins, BM25, metadata filters via normal tables, easy provenance and audit integration. FTS5 is built in. citeturn8search0turn18search11 | No mature built-in vector stack in released SQLite; FTS5 shadow tables and WAL/temp files complicate deletion guarantees. citeturn18search2turn18search6turn18search18 | **Use as source of truth now** |
| **SQLite + sqlite-vec** | Experimental local dense retrieval | Pure C, runs anywhere SQLite runs, metadata columns and filtering, successor to sqlite-vss. citeturn8search1turn19search3turn8search2 | Pre-v1 with expected breaking changes. citeturn8search1 | **Best experimental vector add-on** |
| **SQLite + official vec1** | Future-looking local ANN | Official SQLite vector extension, supports ANN, metadata columns, streaming queries, reranking, cosine/L2, no external dependencies. citeturn21search0turn20view0 | It is not yet at first release; SQLite’s own roadmap notes testing is still insufficient. citeturn21search4 | **Watch closely, do not bet production on it yet** |
| **LanceDB OSS** | Rich embedded local retrieval | Embedded library, vector + full-text + hybrid search, metadata in same table, built-in versioning and reproducibility. citeturn33view4turn33view5turn34search0 | Bigger dependency and format shift than SQLite; less natural as ARC’s universal control plane. | **Strong phase-two option if ARC wants richer embedded retrieval** |
| **Qdrant local mode / Edge** | Local-to-server migration path | Local mode uses same client API as server, Qdrant Edge is in-process and offline capable, hybrid fusion and multitenancy are mature. citeturn33view1turn33view6turn33view7turn34search2 | Heavier operational model than SQLite for a local-first CLI/IDE tool. | **Best if ARC later grows into shared/team retrieval** |
| **Chroma PersistentClient** | Simple prototype vector store | Easy local persistence and metadata filters. citeturn33view3turn34search1 | Chroma docs position PersistentClient for local development/testing and recommend server-backed production. citeturn33view3 | **Lower priority for ARC** |

My concrete recommendation is:

### Phase-one storage choice

Use **SQLite as the canonical store**, replacing `.arc/memory/graph.json` as the primary mutable source of truth. Keep `graph.json` as an export/debug artefact, not the main database.

### Phase-two retrieval choice

Add a backend interface:

- `bm25` via FTS5
- `graph` via adjacency tables
- `dense` via `sqlite-vec` experiment
- later `dense` via official `vec1` if and when it stabilises
- optional `lancedb` backend if evaluation shows material gains

This preserves ARC’s local-first posture while avoiding early lock-in.

## Extraction strategy

ARC already has the most important primitive: **deterministic trace extraction with redaction-before-extraction**. Keep that. Market evidence points away from uncontrolled “the model remembers whatever it wants” designs and towards structured extraction with explicit stores, tools, and schemas. Letta exposes explicit memory blocks and archival writes/search; LangMem provides schema-driven memory extraction and background consolidation; LlamaIndex property-graph construction runs defined extractors over chunks and stores entities/relations as metadata. citeturn27search0turn27search5turn29view2turn29view3turn30view0

I recommend a **two-stage write pipeline**:

### Deterministic candidate generation

From each run, derive structured candidates without an LLM wherever possible:

- files touched
- symbols resolved
- tools used
- failures observed
- retries and recoveries
- provider/model chosen
- latency/cost/error outcomes
- user corrections
- explicit user preferences
- final successful artefacts

This stage should remain highly conservative.

### Schema-bound memory synthesis

Then run a second pass that maps candidates into explicit memory classes:

- **Codebase memory**: conventions, important symbols, architectural hotspots, generated artefact locations
- **Decision memory**: “we chose X over Y because…”
- **Failure memory**: anti-patterns, recurring exceptions, prior unsuccessful strategies
- **Tool-use memory**: tool selection heuristics, parameter patterns, known preconditions
- **Provider/model memory**: which model handled which task well or badly
- **Workspace facts**: persistent preferences or rules
- **Sanitised global patterns**: abstracted templates only

LangMem’s framing is especially useful here: semantic memory for facts, episodic memory for successful prior interactions, and procedural memory for rules or behaviour. ARC should map these directly into stable classes instead of using one amorphous “memory” bucket. citeturn17search0turn29view2

For each memory, bind **evidence** rather than storing bare summaries. Provenance should include at least the originating run, span IDs, source hashes, timestamps, extractor/redactor versions, and an evidence payload small enough to inspect in the IDE or CLI. This is essential if ARC later wants high-quality deletion, replay, and ranking.

For codebase indexing, ARC should borrow from both Continue and Cursor. Continue’s guidance is pragmatic: start simple, then move to AST-based chunking when quality demands it; Cursor uses syntactic chunks and caches embeddings by chunk content; tree-sitter provides incremental parsing and a concrete syntax tree that updates efficiently as files change. citeturn23view2turn22view0turn10search0turn10search8

That suggests a chunking policy like this:

- **Tiny files**: single chunk
- **Normal files**: tree-sitter symbol chunks for classes, functions, methods, top-level declarations
- **Very large files**: recursive tree-sitter subdivision with bounded token targets
- **Fallback**: fixed-size chunks only for unsupported languages or parse failures

Each code chunk should store path hash, language, symbol path, imports/exports, start/end lines, content hash, and optional short contextual header. That contextual header is worth doing for longer prose-heavy artefacts and docs: Anthropic’s contextual retrieval work found that prepending short chunk-specific context improved retrieval materially, especially when combined with BM25 and reranking. citeturn25view2

The most important extraction rule is this: **write fewer memories, but better ones**. OpenAI explicitly says memory is best for high-level preferences/details rather than exact templates or large verbatim text. ARC should follow the same discipline and avoid stuffing raw trace logs or long code blobs into reusable memory. citeturn26view0

## Retrieval, ranking, and runtime integration gates

The retrieval strategy should be **hybrid from day one**, even if dense vectors stay off at first. Cody combines keyword search, repository search, and code graph context; Sourcegraph’s own research argues the retrieval phase should optimise for recall via complementary sources, while the ranking phase should optimise for precision under latency and token constraints. Anthropic’s contextual retrieval results reinforce that simple dense-only RAG is not enough; contextual embeddings plus contextual BM25 reduced top-20 retrieval failure substantially, and reranking improved it further. citeturn22view4turn24view1turn25view2

ARC’s retrieval stack should therefore be:

### Candidate generation

Pull from multiple sources in parallel:

- workspace policy and exact metadata filters
- code symbol graph neighbourhood
- FTS5 BM25 over code chunks and memory summaries
- optional dense search over code chunks or selected memory classes
- recent-run recovery patterns
- provider/model memory for the active task type

### Ranking

Then rank with a transparent composite score:

`score = lexical + graph + semantic + recency + success_prior + workspace_affinity + provenance_quality - staleness - privacy_risk`

Qdrant’s hybrid guidance is useful here: if you have an eval set, tune weighted fusion; if not, use RRF as a safe default; then layer custom formula scoring for business logic such as recency or policy priority. ARC can use the same philosophy even if it does not literally use Qdrant. citeturn33view7

### Retrieval by memory type

Not all memory should retrieve the same way.

- **Codebase indexing** should prefer symbol/keyword/graph retrieval first.
- **Decision memory** should prefer exact workspace filters and recency.
- **Failure memory** should retrieve aggressively when the current run shows matching tool/error signatures.
- **Tool-use memory** should retrieve only when the active toolset overlaps.
- **Provider/model memory** should retrieve only for the current provider/model or task family.
- **Cross-workspace sanitised memory** should rank last and only after workspace-local candidates.

This is important because the biggest real risk is not retrieval failure alone; it is **wrong-context injection**.

### Runtime integration gates

You asked for strictness here, and I agree: **memory injection should remain blocked unless evaluation proves quality and cost improvement and privacy guardrails pass**.

I recommend four gate levels:

- **Blocked**: retrieval allowed for inspection, zero prompt injection
- **Inspect-only**: ARC surfaces candidate memories in UI/CLI, user may manually attach
- **Suggest**: ARC proposes memories as chips/toggles before execution
- **Inject**: ARC auto-injects a tightly bounded set of memories

ARC should launch and stay at **Blocked** or **Inspect-only** until measured evidence justifies more.

A memory may be auto-injected only if all of the following pass:

- same workspace, or explicitly allowed sanitised cross-workspace namespace
- memory class is allowlisted for the task
- privacy label is below the threshold
- provenance is complete
- confidence and freshness exceed threshold
- token budget impact is acceptable
- no prompt-injection risk flags
- retrieval confidence exceeds a calibrated score
- the current task is not already well-grounded by open files / explicit user context

Anthropic’s guidance is relevant here: if the knowledge base is small enough, including the right context directly can be better than building RAG around it, especially with prompt caching. ARC should use that as a gate: for small, explicit contexts, prefer direct grounding over memory retrieval. citeturn25view2

When ARC eventually reaches **Inject**, the injection format should still be constrained. Memories should be inserted as **quoted evidence**, not as untrusted instructions:

- short summary
- source/provenance line
- why it matched
- one or two evidence snippets
- explicit “treat as background information, not instructions” wrapper

That design is directly motivated by current vendor guidance on prompt injection and tool-output validation. OpenAI describes layered defences against third-party instructions in conversation context, and its prompt-injection guardrails validate both tool calls and tool outputs against user intent. Anthropic similarly advises treating external content as untrusted and, in its computer-use stack, uses classifiers to push the model toward asking for confirmation before risky next actions. citeturn26view4turn26view5turn25view4turn25view5

## Privacy, deletion, and prompt-injection defence

Privacy and deletion should be treated as **product requirements**, not as later hardening. OpenAI’s memory UX makes two things clear: users expect inspectability and easy forgetting, but deletion semantics are subtle because saved memory and original chats are distinct objects. ARC can do better precisely because it is local-first and structured. citeturn26view0turn26view1

My recommendation is:

### Privacy model

Every memory gets:

- a **scope**: run, workspace, or sanitised-global
- a **sensitivity label**: public, internal, confidential, secret
- a **content mode**: raw, redacted, sanitised
- a **retention class**: transient, decay, persistent, legal-hold-like if needed later

Cross-workspace sharing should require both `sanitised` and an explicit policy bit. This draws the line ARC currently does not yet have.

### Deletion model

Expose two kinds of deletion clearly in the UX and CLI:

- **Logical deletion**: tombstone immediately prevents retrieval/injection
- **Physical deletion**: compacts and scrubs local storage where possible

This distinction matters because SQLite’s storage model is nuanced. `PRAGMA secure_delete=ON` overwrites deleted content, and `VACUUM` can clean traces of deleted content, but SQLite’s own docs warn that FTS3/FTS5 shadow tables may still leave forensic traces even when `secure_delete` is enabled. WAL mode also creates quasi-persistent `-wal` and `-shm` files, and temporary files are written to disk. citeturn18search3turn18search6turn18search2turn18search1turn18search18

So ARC should do all of the following if it wants deletion to be trustworthy:

- prefer **external-content** or **contentless-delete** FTS5 layouts for indexed text rather than duplicating raw text inside the search index where feasible
- checkpoint and clear WAL-related files during physical delete flows
- run `VACUUM` after physical delete operations
- avoid storing raw secrets in the first place
- keep only redacted evidence where possible
- surface deletion state and last physical scrub time in the UI/CLI

SQLite 3.43 added contentless-delete FTS5 indexes specifically to allow deletion while omitting stored content. That is extremely relevant to ARC because it reduces duplicated raw content in the index and improves the odds of meaningful physical deletion. citeturn18search11

### Prompt-injection defence

Memory is a prompt-injection surface the moment it is ever injected at runtime. OpenAI defines prompt injection as malicious instructions from a third party embedded in conversation context; Anthropic makes the same point for browser agents, where invisible or irrelevant instructions can hijack behaviour. ARC should therefore treat **retrieved memory, retrieved docs, tool outputs, and imported traces as untrusted data**. citeturn26view4turn25view4

The practical defences I recommend are:

- **Write-time scanning** for instruction-like content in candidate memories
- **Read-time scanning** before any candidate enters a prompt
- **Instruction/data separation** in the prompt template
- **Tool-call validation** before execution
- **Tool-output validation** after execution
- **Human confirmation** when risky actions are influenced by retrieved context
- **No memory-to-policy writes** without explicit approval

In other words: ARC may remember that “running tool X before tool Y fixed this class of error,” but it should not silently convert arbitrary retrieved text into executable behavioural rules.

## Evaluation strategy

ARC should not claim “production memory” until it passes three separate tests: **retrieval quality**, **end-to-end task lift**, and **privacy/safety boundaries**. The research base is clear that long-term memory is hard to evaluate and that bigger context windows do not remove the need for proper memory systems. LoCoMo evaluates very long-term conversational memory across QA, summarisation, and temporal reasoning; LongMemEval focuses on information extraction, multi-session reasoning, temporal reasoning, knowledge updates, and abstention; newer work on memory-agent evaluation via incremental interactions argues that memory itself needs dedicated benchmarks rather than being treated as a side effect of agent performance. citeturn11search4turn11search6turn11search13

Sourcegraph’s Cody research adds an important engineering lesson: evaluate retrieval and ranking separately, but also measure end-to-end utility, because context engines suffer from a large offline/online gap and many useful context sources are local, ephemeral, or difficult to log safely. citeturn24view1

I recommend ARC extend `arc memory evaluate` into five suites.

### Retrieval evaluation

Measure:

- recall@k
- MRR / nDCG
- exact workspace-boundary correctness
- stale-memory retrieval rate
- wrong-memory top-k rate

Use labelled queries over real ARC traces and codebases. For code retrieval, include repository-level tasks similar in spirit to CodeRAG-bench, which was introduced precisely because code RAG needs both retrieval and end-to-end evaluation across different task types and sources. citeturn10search13

### Extraction evaluation

Measure:

- precision/recall of extracted memory items against a reviewed gold set
- redaction correctness before extraction
- stability across reruns
- provenance completeness
- duplicate rate
- over-abstraction rate

### End-to-end task evaluation

Measure whether memory actually improves:

- grounded answer preference
- correct tool selection
- error recovery rate
- successful completion rate
- retained code changes
- latency and token cost deltas

Anthropic’s contextual retrieval work is a good benchmark for the kind of measurable lift ARC should demand from retrieval improvements rather than assuming they help. citeturn25view2

### Safety and privacy evaluation

Measure:

- cross-workspace leak rate
- secret/PII retention rate
- deletion success rate
- prompt-injection attack success rate
- unsafe tool-call rate influenced by memory
- false-confidence memory rate

### Rollout gating

ARC should codify an explicit release gate such as:

- **no auto-injection** unless held-out evals show meaningful improvement on grounded task success or answer preference,
- **no regression** on privacy and safety tests,
- **bounded cost increase**,
- and **successful live A/B validation**.

I would set the default organisational policy to: **memory retrieval may ship before memory injection; memory injection may not ship before evaluation-backed approval**.

## IDE and CLI experience

ARC’s UX should make memory **inspectable, correctable, and optional**. OpenAI lets users ask what is remembered, delete individual memories, or use Temporary Chat when they want a blank slate; Claude Projects separate project knowledge from ordinary chats and explicitly state that context is not shared across project chats unless it is added to project knowledge. Those product decisions are worth copying because they make boundaries legible to users. citeturn26view0turn26view2turn25view1

### IDE UX for memory

The IDE should get a **Memory** panel with five tabs:

- **Workspace**
- **Decisions**
- **Failures**
- **Tools**
- **Models**

Every memory card should show:

- short summary
- scope
- provenance
- freshness
- confidence
- why it matched
- whether it was injected, suggested, or ignored

The crucial interaction is not just “remember this.” It is:

- **show me why ARC thinks this matters**
- **let me attach or reject it for this turn**
- **let me delete it**
- **let me pin or demote it**
- **let me see which memories were retrieved but kept out of the prompt**

I would also add a **Memory write review** tray after each run. Letta’s explicit memory tools and block management are relevant inspiration here: editable, inspectable memory is safer and easier to debug than hidden automatic memory. citeturn27search0turn27search14

### CLI UX for memory

Keep the current commands, but extend them rather than inventing a parallel UX. A good shape would be:

- `arc memory extract --review`
- `arc memory query --why`
- `arc memory show <id> --provenance --evidence`
- `arc memory forget-run <run-id> --logical|--physical`
- `arc memory approve <candidate-id>`
- `arc memory reject <candidate-id>`
- `arc memory gc`
- `arc memory stats`
- `arc memory audit --scope workspace`
- `arc memory evaluate --suite retrieval|extraction|e2e|privacy|injection`
- `arc index build`
- `arc index status`
- `arc index explain <query>`

The most important CLI additions are `--why`, `--provenance`, and physical-vs-logical delete flags. If ARC cannot explain a memory retrieval or a deletion outcome, the feature will be hard to trust.

## Top memory features

The strongest feature inspirations in the list below come from Letta’s explicit split between in-context and archival memory, LangGraph/LangMem’s types and stores, Continue’s local indexing, Cursor’s incremental Merkle-based indexing, Cody’s multi-source context engine, Anthropic’s contextual retrieval and prompt-injection guidance, OpenAI’s memory controls, and the storage capabilities of SQLite, sqlite-vec, vec1, LanceDB, Qdrant, and Chroma. citeturn27search0turn27search5turn29view1turn29view2turn23view0turn22view0turn22view4turn25view2turn26view0turn8search0turn8search1turn21search0turn33view4turn33view6turn33view3

My top fifteen features for ARC, in priority order, are:

| Feature | Source inspiration | Benefit | Privacy risk | Complexity | Evaluation metric | Priority |
|---|---|---|---|---|---|---|
| Workspace-scoped memory namespaces | LangGraph stores, Claude Projects, ChatGPT Projects | Strong default isolation and clearer UX | Low | Medium | Cross-workspace leak rate | P0 |
| Memory provenance ledger | LangGraph persistence, Letta explicit memory, SQLite auditability | Debuggability, trust, deletion traceability | Low | Medium | % memories with complete provenance | P0 |
| Dedicated codebase index separate from memory | Cursor, Continue, Cody | Better code retrieval and less memory pollution | Medium | High | Repo task success, recall@k | P0 |
| Hybrid retrieval | Cody, Anthropic contextual retrieval, Qdrant hybrid fusion | Better recall and precision than single-source retrieval | Medium | High | nDCG, answer preference | P0 |
| Runtime memory gates with default block | OpenAI guardrails, Anthropic confirmation pattern | Prevents premature unsafe injection | Low | Medium | Unsafe injection rate | P0 |
| Decision memory | LangMem procedural memory | Preserves rationale, reduces repeated debate | Medium | Medium | Fewer repeated decision errors | P1 |
| Failure memory | LangMem episodic memory, ARC traces | Faster recovery from repeated mistakes | Medium | Medium | Error recurrence rate | P1 |
| Tool-use memory | Anthropic tool guidance, Letta tools | Better tool selection and parameter choice | Medium | Medium | Tool success / fewer retries | P1 |
| Provider/model memory | Prompting and long-context guidance | Better model routing, lower cost | Low | Medium | Task win-rate by model | P1 |
| Tree-sitter symbol chunking | Tree-sitter, Continue AST chunking, Cursor syntactic chunks | Better code chunk semantics and incremental reindexing | Low | High | Retrieval precision on code queries | P1 |
| Memory decay and refresh | Consumer memory lessons, long-term memory research | Keeps store small and current | Low | Medium | Stale-memory retrieval rate | P1 |
| Sanitised cross-workspace pattern store | Project/workspace boundary patterns | Reuse without raw leakage | High | High | Leak rate, reuse lift | P1 |
| Physical deletion workflow | OpenAI deletion controls, SQLite VACUUM/secure_delete | Trustworthy forgetting | High | Medium | Verified delete success rate | P1 |
| Injection-safe memory formatting | OpenAI/Anthropic prompt-injection guidance | Reduces instruction hijack risk | Medium | Low | Prompt-injection success rate | P0 |
| Memory review UX in IDE/CLI | Letta explicit memory tools, OpenAI manage memories | User trust and fast correction loop | Low | Medium | Review acceptance / rejection quality | P1 |

A few features deserve especially strong emphasis.

**Best immediate wins** are workspace namespaces, provenance, a dedicated codebase index, hybrid retrieval, and blocked-by-default runtime gates. Those are the features most likely to improve ARC quickly without overstating what memory can do.

**Best medium-term wins** are failure memory, decision memory, and tool-use memory, because they convert deterministic traces into learning that is actually useful on future runs.

**Highest-risk feature** is cross-workspace memory. It is valuable, but only as a sanitised derivative layer with strict policy and evaluation.

### Open questions and limitations

This report assumes the ARC status in your brief is complete and authoritative. I did not rely on additional internal ARC Studio documents beyond that brief.

There are also two external uncertainties worth calling out plainly:

- **Official SQLite vec1 is promising but not yet first-release-stable**, and SQLite’s own roadmap still flags testing as insufficient. It is worth watching, but not yet the safest default backend for ARC memory retrieval. citeturn21search0turn21search4
- **Deletion guarantees in local search stacks are subtle**, especially with FTS shadow tables and WAL/temp files. ARC should present deletion semantics honestly and distinguish logical from physical deletion in both UX and docs. citeturn18search2turn18search6turn18search18

The bottom-line recommendation is therefore:

**Ship ARC memory as a local-first, workspace-scoped, provenance-heavy subsystem with retrieval and inspection first; keep automatic runtime injection blocked until ARC’s own evaluations show a real win on grounded tasks with no privacy regressions.**