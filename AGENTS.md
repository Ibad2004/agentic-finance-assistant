# AI-Powered Agentic Finance and Tax Assistant

## Project scope

This project is an AI-Powered Agentic Finance and Tax Assistant.

The approved MVP stack is:

- Python
- FastAPI
- LangGraph
- PostgreSQL
- Groq as the initial LLM provider
- CSV/sample financial data as the initial data source

Do not add MongoDB, a vector database, or real banking APIs unless there is a demonstrated MVP requirement. The CSV-based workflow must work correctly before real banking integrations are considered.

## Tax scope

The MVP tax scope is limited to:

- United Kingdom: England
- Tax year: 2026/27
- Income Tax estimation only

Do not implement Scotland, Wales, Northern Ireland, VAT, HMRC submission, multi-country tax support, or other tax types in the initial MVP.

Tax rules must:

- Be separate from the Tax Agent.
- Be implemented with deterministic Python logic.
- Be versioned by tax year.
- Be verified against official GOV.UK/HMRC sources before implementation; never implement tax rules from model memory.
- Save the applied rules version with each tax calculation result.
- Include assumptions and limitations in every tax result.
- Never present an estimate as an official HMRC determination.

The Tax Agent must not contain tax thresholds, rates, bands, or arithmetic. The England tax engine owns tax rules and calculations.

## Architecture rules

1. Keep agents, tools, services, database access, API routes, and tax logic separate.
2. Agents decide and coordinate work.
3. Tools perform controlled actions.
4. Agents must never have unrestricted SQL access.
5. Database access must follow this path:

   ```text
   Agent -> Tool -> Service/Repository -> PostgreSQL
   ```

6. PostgreSQL is the source of truth for structured financial data.
7. Every financial record and query must be scoped to the authenticated user.
8. Use fixed-precision decimal types for financial amounts. Never use floating-point values for financial calculations.
9. Critical financial calculations must be deterministic Python code.
10. Financial reports must be generated from validated structured data, never invented by an LLM.
11. Agents should communicate through controlled LangGraph workflows and shared state. They must not arbitrarily call other agents.
12. Tool outputs should preferably be structured data rather than free-form text.

## LLM rules

The LLM is not trusted to perform:

- Financial arithmetic
- Tax calculations
- Budget totals
- Report totals

The LLM should primarily handle:

- Natural-language understanding
- Request routing
- Categorization where appropriate
- Interpretation of verified tool results
- Natural-language explanations

Keep LLM integration behind a provider-neutral interface so Groq can later be replaced by Gemini or another provider without rewriting agents.

Treat all LLM output as untrusted. Validate it before using it in application workflows. Never allow an LLM to execute arbitrary SQL.

## Agent rules

- Do not create agents merely to increase the number of agents.
- Use deterministic services and tools for deterministic tasks.
- Each agent must have a clear, limited responsibility.
- LangGraph coordinates agents and workflows.
- Agents use only approved tools to access data and perform actions.
- Agent results must be traceable to validated data and deterministic calculations where applicable.

## Security rules

- Never hardcode API keys, passwords, tokens, or database credentials.
- Use environment variables or an approved secret manager for secrets.
- Never expose secrets in logs, errors, tests, or documentation.
- Authenticate all user-specific API routes.
- Scope all database queries to the authenticated user.
- Validate imported CSV files, including structure, supported fields, dates, amounts, file size, and duplicate data where applicable.
- Record important sensitive actions in audit logs.
- Do not expose raw database errors to users.
- Do not perform external financial actions without explicit user confirmation.
- Apply least-privilege access to databases and external services.

## Development rules

- Do not modify unrelated files.
- Do not delete or remove existing functionality without user approval.
- Keep functions, classes, and modules focused on one responsibility.
- Prefer readable, maintainable code over unnecessarily clever code.
- Add tests for important functionality, especially financial calculations, tax calculations, imports, authorization, and data scoping.
- Run relevant tests after implementation and report the results.
- Explain significant architectural changes before implementing them.
- Do not commit or push to GitHub without explicit user approval.

## Git rules

- Never commit automatically.
- Never push automatically.
- Keep feature changes focused.
- Before a commit, show the user the changed files and relevant test results.

## Documentation rules

- Document important architectural decisions.
- Keep the README and architecture documentation updated as the project develops.
- Document tax assumptions, sources, supported scope, and limitations alongside the tax engine.
