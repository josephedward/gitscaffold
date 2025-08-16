# Integration Testing (Markdown-first)

 This document demonstrates integration testing using unstructured Markdown roadmaps as the primary flow. Gitscaffold uses AI to extract and enrich issues from free-form Markdown.

 ## 1. Create a test Markdown roadmap

 In your local checkout, create `markdown_roadmap.md` with content like:

```markdown
 # Authentication Service
 Implement login, logout, and registration flows.

 ## Database Schema
 - Define `users` table with fields: id, email, password_hash
 - Define `sessions` table with fields: id, user_id, expires_at

 # Payment Integration
 Enable subscription payments with Stripe.

 ## Stripe Webhook
 - Listen to payment events and update user plans
```

 ## 2. Smoke-test the CLI with Markdown import

```sh
 pip install -e .
 export OPENAI_API_KEY=<your-openai-key>
 export GITHUB_TOKEN=<your-pat>

 # Dry-run: extract & enrich without creating
 gitscaffold import-md your-user/test-gitscaffold markdown_roadmap.md \
   --heading-level 1 \
   --dry-run

 # Full run: create issues & apply enriched bodies
 gitscaffold import-md your-user/test-gitscaffold markdown_roadmap.md \
   --heading-level 1
```

 ## 3. Test as a GitHub Action

In your test repo (e.g. `your-user/test-gitscaffold`), add `markdown_roadmap.md` and a workflow file under `.github/workflows/scaffold-md.md`:

```
name: Scaffold Markdown Test
on: [push]
jobs:
  scaffold:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install Gitscaffold
        run: pip install gitscaffold
      - name: Import Markdown roadmap
        run: |
          gitscaffold import-md ${{ github.repository }} markdown_roadmap.md \
            --heading-level 1 \
            --dry-run
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }} # Assuming action needs OpenAI key
```

 Push and observe the Action logs. Then switch `dry-run` to `false` to create issues.

 ## 4. Local Action simulation with act

```sh
 act push -j scaffold
```

 And you're done!
