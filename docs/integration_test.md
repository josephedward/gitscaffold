# Integration Testing

This document demonstrates integration testing using structured YAML roadmap files. For unstructured Markdown imports, see the `import-md` command in the CLI documentation (README.md).

## Unstructured Markdown Example

When you have a free-form Markdown document instead of a structured YAML roadmap, use the `import-md` command to extract and enrich issues automatically. Create a file named `markdown_roadmap.md` with content like:

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

Then run:

```sh
export OPENAI_API_KEY=<your-openai-key>
# Preview extracted and enriched issue bodies without creating on GitHub
gitscaffold import-md your-user/test-gitscaffold markdown_roadmap.md \
  --dry-run --token $GITHUB_TOKEN

# To actually create and enrich issues on GitHub:
gitscaffold import-md your-user/test-gitscaffold markdown_roadmap.md \
  --apply --token $GITHUB_TOKEN
``` 

Here’s a quick “integration‐test” recipe for both the CLI and the GitHub Action. You don’t need to touch your production repos—just spin up a throw-away repo on GitHub (or locally with act) and a fake roadmap file:

1. Prepare a throw-away GitHub repo  
   • Create a new empty repo on GitHub, e.g. `your-user/test-gitscaffold`  
   • Generate a Personal Access Token (PAT) with “repo” scope and export it locally:

       ```sh
       export GITHUB_TOKEN=ghp_…yourPAT…
       ```

2. Smoke-test the CLI locally  
   a. Create a `fake-roadmap.yml` alongside your code:

       ```yaml
       name: Test Project
       description: Quick smoke test
       milestones:
         - name: MVP
           due_date: 2099-12-31
       features:
         - title: “Hello World”
           description: “Just a test”
           milestone: MVP
       ```

   b. Dry-run against your test repo:

       ```sh
       pip install -e .          # or pip install gitscaffold if published
       gitscaffold create fake-roadmap.yml \
         --repo your-user/test-gitscaffold \
         --token $GITHUB_TOKEN \
         --dry-run
       ```

   → You should see printed steps but no API calls.  
   c. Real run: drop `--dry-run`. Inspect your test repo’s Issues & Milestones to confirm.

3. Set up and test the GitHub Action  
   In your throw-away repo, add:  
   • **roadmap.yml** (same content as above) at repo root  
   • **.github/workflows/scaffold.yml**:

       ```yaml
       name: Scaffold Test
       on: [push]
       jobs:
         test:
           runs-on: ubuntu-latest
           steps:
             - uses: actions/checkout@v3
             - name: Run gitscaffold
               uses: your-user/gitscaffold-action@v0.1.1  # or `./` for local
               with:
                 roadmap-file: roadmap.yml
                 repo: your-user/test-gitscaffold
                 github-token: ${{ secrets.GITHUB_TOKEN }}
                 dry-run: 'true'
       ```

   • Commit & push → GitHub Actions tab  
   • Confirm the “Run gitscaffold” step prints your planned milestones/issues.  
   • Flip `dry-run: 'false'` to actually create them.

4. (Optionally) test entirely locally with [act](https://github.com/nektos/act):

       ```sh
       brew install act       # or your platform’s preferred install
       act push -j Scaffold   # simulate the above workflow on your machine
       ```

— That’s it! You now have a fully isolated sandbox, a fake roadmap, and both CLI and Action runs to iterate on without touching production.
