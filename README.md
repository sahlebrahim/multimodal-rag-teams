# Multimodal RAG in Microsoft Teams

A RAG agent that answers from a PDF and shows the
diagrams, charts, and screenshots referenced in its answers.
Built two ways
over the same corpus: low code (Copilot Studio + Teams) and code first
(Azure AI Foundry).

## Status
Work in progress

## Architecture


## Repo layout
- `ingestion/` : PDF → markdown + extracted images
- `enrichment/` : vision-model image descriptions injected into the markdown
- `infra/` : Bicep templates (resource group, storage, Azure AI Search)
- `search/` : index, skillset, data source, indexer definitions
- `function_app/` : Azure Function that resolves a filename to a SAS image URL
- `agent/` : code-first Foundry agent (retrieve-then-generate)
- `eval/` : retrieval + image-attachment evaluation harness
- `docs/` : architecture notes and teardown

## License
MIT