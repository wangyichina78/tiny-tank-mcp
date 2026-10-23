# Disclaimer

This package — the code, tests, tools and documents — is **reference material**. It was produced as a learning exercise and proof of concept to show how an MCP server can be built, tested, secured and published. It is shared so others can learn from the approach. It is not a product, and it is not offered for direct use.

## Review before any use

Nothing in this package should be adopted into a work, test or production environment as it is. Before any part of it is used, copied or adapted, it should be independently reviewed and vetted by the people responsible for that environment. That review would normally include:

- a code review against your own standards;
- a security review under your own policies and approval process;
- a check of all dependencies, their versions and their licence terms;
- testing in your own environment, with your own data, network and platform settings.

The tests and security checks in this package show how the reference server behaved in the configuration and on the dates described in its documents. Those results don't carry over automatically to another environment, another version, or a modified copy. They are examples of what to verify, not evidence that your own deployment is safe.

## Responsibility

Anyone who uses, copies, adapts or deploys any part of this package does so on their own decision and takes full responsibility for that use. That includes its security, its fitness for their purpose, and its compliance with their organisation's policies, applicable laws and regulations, data protection requirements, and the terms of any third-party software or service involved.

## No warranty

The package is provided "as is", without warranty of any kind, express or implied. That includes, without limitation, any warranty of accuracy, completeness, security, merchantability or fitness for a particular purpose. The authors and contributors are not liable for any claim, loss or damage arising from its use or from reliance on it.

## Things to be aware of

- **Synthetic data.** All tank data is invented for testing. It doesn't describe any real site, asset or organisation.
- **No authentication.** The reference server deliberately has none. That is acceptable only for synthetic data on a short-lived test endpoint. Any use with real data needs authentication and authorisation designed for that environment.
- **AI-assisted work.** The code and documents were written with the help of an AI assistant (Claude) and tested as described. They may still contain errors or omissions.
- **Point in time.** Statements about the MCP specification, the MCP Python SDK, hosting platforms and agent platforms reflect what was observed when the documents were written (October 2026). These things change. Statements marked *Inferred* or *Judgment* in the documents were not directly tested.
- **Third-party names.** Products and services mentioned (including the MCP Python SDK, GitHub, Render, Cloudflare, Microsoft Copilot Studio and Claude) are named to describe how the work was done. Their mention implies no affiliation or endorsement, and their own terms apply.
- **No support or maintenance.** The package isn't maintained and may not be updated.

No licence is granted beyond what applicable law allows. If you need clarity on what you may do with this material in your organisation, ask your legal or compliance team.
