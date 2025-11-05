Run a quick chain execution with the provided prompt: $ARGUMENTS

Steps:
1. Parse the user's request
2. Execute: `mao-chain "$ARGUMENTS"`
3. Monitor progress (builder → critic → closer)
4. Display summary of results
5. Save output to `chain-output-$(date +%Y%m%d-%H%M%S).md` if successful

Use this for quick multi-agent workflows without manual command typing.

Example: /quick-chain Design a REST API for user authentication
