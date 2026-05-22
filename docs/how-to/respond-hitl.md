# How to Respond to HITL Prompts

**Goal:** Respond to Human-in-the-Loop (HITL) approval requests during workflow execution.

**Time:** 1-2 minutes per prompt  
**Prerequisites:**
- A workflow that requests HITL approval
- Pending HITL prompts

---

## What is HITL?

Human-in-the-Loop (HITL) allows workflows to request human approval before proceeding with certain actions.

**Common use cases:**
- **High-risk operations:** Delete data, make purchases, send emails
- **Compliance:** Human oversight required by policy or regulation
- **Quality control:** Human review of AI-generated content
- **Decision points:** Choose between multiple options

**How it works:**
1. Workflow reaches a decision point
2. Workflow pauses and creates a HITL prompt
3. Human reviews the prompt and responds (approve/reject)
4. Workflow resumes with the human's decision

---

## Step 1: Check for Pending Prompts

### List All Pending Prompts

```bash
cd python
uv run arc hitl pending
```

**Output shows:**
- Prompt ID
- Run ID
- Prompt text
- Created timestamp
- Expiration (if set)

**Example:**
```
Pending HITL Prompts:

1. Prompt: hitl_abc123
   Run: run_def456
   Created: 2026-05-22 05:00:15
   Expires: 2026-05-22 06:00:15
   
   "Approve deletion of 150 files?"
   
2. Prompt: hitl_xyz789
   Run: run_ghi012
   Created: 2026-05-22 05:05:30
   
   "Send email to 500 recipients?"
```

### Check Prompts for a Specific Run

```bash
uv run arc hitl pending --run-id <run-id>
```

---

## Step 2: Review the Prompt

Get detailed information about a prompt:

```bash
uv run arc hitl pending --prompt-id <prompt-id>
```

**Details include:**
- Full prompt text
- Context (what the workflow is trying to do)
- Options (approve/reject, or custom choices)
- Metadata (run ID, workflow ID, timestamp)
- Expiration time (if set)

**Example:**
```
HITL Prompt: hitl_abc123

Run: run_def456
Workflow: data-cleanup
Created: 2026-05-22 05:00:15
Expires: 2026-05-22 06:00:15 (54 minutes remaining)

Prompt:
  "The workflow wants to delete 150 files that haven't been 
   accessed in 90 days. This action cannot be undone.
   
   Files to delete:
   - /data/old-logs/*.log (120 files)
   - /data/temp/*.tmp (30 files)
   
   Total size: 2.3 GB
   
   Approve deletion?"

Options:
  - approve: Proceed with deletion
  - reject: Cancel deletion and stop workflow
```

---

## Step 3: Respond to the Prompt (CLI)

### Approve

```bash
uv run arc hitl respond <prompt-id> approve
```

**With notes:**

```bash
uv run arc hitl respond <prompt-id> approve \
  --notes "Reviewed file list, safe to delete"
```

### Reject

```bash
uv run arc hitl respond <prompt-id> reject
```

**With notes:**

```bash
uv run arc hitl respond <prompt-id> reject \
  --notes "Some files still needed, do not delete"
```

### Response Confirmation

After responding, you'll see:

```
HITL Response Recorded

Prompt: hitl_abc123
Decision: approve
Notes: Reviewed file list, safe to delete
Timestamp: 2026-05-22 05:10:00

The workflow will resume with your decision.
```

---

## Step 4: Respond to the Prompt (IDE)

### From the Runs Tab

1. Open ARC Studio: `pnpm start:browser:arc`
2. Click the ARC icon in the left sidebar
3. Go to the **Runs** tab
4. Click **HITL** button to load pending prompts
5. Review the prompt details
6. Click **Approve** or **Reject**
7. (Optional) Add notes
8. Confirm your decision

### From the HITL Widget

1. Open the **HITL** widget (if available)
2. See all pending prompts
3. Click on a prompt to view details
4. Click **Approve** or **Reject**
5. (Optional) Add notes
6. Confirm your decision

---

## Step 5: Verify Response

Check that your response was recorded:

```bash
uv run arc hitl pending --prompt-id <prompt-id>
```

If the prompt is no longer in the pending list, it was successfully responded to.

**Check run status:**

```bash
uv run arc runs status <run-id>
```

The run should have resumed after your response.

---

## HITL Tokens (Security)

Some HITL prompts require a security token to respond. This prevents unauthorized approvals.

### Respond with Token

```bash
uv run arc hitl respond <prompt-id> approve --token <token>
```

**Where to get the token:**
- Sent via email (if configured)
- Shown in the workflow output
- Available in the HITL prompt details

**Example:**
```bash
uv run arc hitl respond hitl_abc123 approve \
  --token "sec_xyz789" \
  --notes "Verified via email token"
```

---

## HITL Expiration

HITL prompts can expire if not responded to within a time limit.

### Check Expiration

```bash
uv run arc hitl pending
```

Shows time remaining for each prompt.

### What Happens When Expired

- Prompt is automatically rejected
- Workflow fails with "HITL timeout" error
- No further action is taken

### Extend Expiration (Not Yet Supported)

Currently, you cannot extend the expiration time. Respond before it expires.

---

## Troubleshooting

### "Prompt not found"

**Problem:** `arc hitl respond` fails with "HITL prompt not found"

**Solution:**
1. Check the prompt ID is correct
2. List pending prompts: `uv run arc hitl pending`
3. The prompt may have expired or already been responded to
4. Check if the prompt was for a different workspace

---

### "Token mismatch"

**Problem:** Response fails with "Token mismatch" or "Invalid token"

**Solution:**
1. Check the token is correct (copy it carefully)
2. Tokens are case-sensitive
3. Check for extra spaces or newlines
4. If token was sent via email, check spam folder
5. Request a new token (not yet supported)

---

### "Prompt already responded"

**Problem:** Response fails with "Prompt already responded to"

**Solution:**
1. Someone else may have already responded
2. Check the run status to see the decision
3. If the wrong decision was made, you may need to re-run the workflow

---

### "Prompt expired"

**Problem:** Response fails with "Prompt expired" or "HITL timeout"

**Solution:**
1. The prompt expired before you responded
2. Check the expiration time: `uv run arc hitl pending`
3. Re-run the workflow and respond faster
4. Or request longer expiration time (requires workflow change)

---

### Workflow doesn't resume

**Problem:** After responding, the workflow doesn't continue

**Solution:**
1. Check run status: `uv run arc runs status <run-id>`
2. If status is "failed", check the autopsy: `uv run arc runs autopsy <run-id>`
3. The workflow may have failed for another reason
4. Check the trace for errors: `uv run arc runs export <run-id>`

---

## Best Practices

### Review Carefully

- **Read the full prompt:** Don't approve without understanding what you're approving
- **Check the context:** Understand why the workflow is asking
- **Review the data:** If the prompt includes data (files to delete, emails to send), review it
- **Consider the impact:** What happens if you approve? What happens if you reject?

### Add Notes

- **Document your decision:** Add notes explaining why you approved or rejected
- **Include evidence:** Reference external sources (tickets, emails, policies)
- **Help future reviewers:** Your notes may help others understand the decision

### Respond Promptly

- **Don't let prompts expire:** Respond before the expiration time
- **Set up notifications:** Configure email/Slack notifications for HITL prompts (if available)
- **Delegate if needed:** If you can't respond, delegate to someone who can

### Use Tokens for High-Risk Operations

- **Require tokens:** For high-risk operations (delete data, make purchases), require tokens
- **Verify tokens:** Always verify the token before responding
- **Don't share tokens:** Tokens are security credentials, don't share them

---

## Advanced: Bulk Responses

If you have many pending prompts, you can respond to them in bulk.

### Approve All Prompts for a Run

```bash
for prompt_id in $(uv run arc hitl pending --run-id <run-id> --json | jq -r '.prompts[].promptId'); do
  uv run arc hitl respond $prompt_id approve --notes "Bulk approval"
done
```

### Reject All Expired Prompts

```bash
# Not yet supported - prompts auto-reject on expiration
```

**Warning:** Bulk responses can be dangerous. Review each prompt individually unless you're certain.

---

## Next Steps

After responding to HITL prompts:

- **[Inspect the trace](./inspect-trace.md)** to see how the workflow proceeded
- **[View the run receipt](./inspect-trace.md#view-receipt)** to see the final outcome
- **[Compare runs](./compare-runs.md)** to see how different decisions affect outcomes

---

## Related Documentation

- **[HITL Architecture](../explanation/hitl.md)** — How HITL works (to be created)
- **[Security Model](../explanation/security.md)** — HITL token security
- **[Workflow Guide](../how-to/write-workflow.md)** — How to add HITL to workflows (to be created)
- **[Error Codes](../reference/error-codes.md)** — HITL-related error codes
