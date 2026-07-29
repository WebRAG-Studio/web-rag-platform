# Architecture

SiteMind separates control, content, retrieval, and generation.

1. **API and dashboard** create and manage site configurations.
2. **Crawler** validates every URL, respects robots.txt by default, follows same-domain links, and records atomic progress checkpoints.
3. **Ingestion** validates files, extracts selectable PDF text, and optionally OCRs low-quality pages.
4. **Storage** assigns every site an isolated directory containing configuration, content, state, and index files.
5. **Retrieval** performs exact document matching first, then lexical and vector scoring, with OCR-quality penalties.
6. **Generation** sends only selected evidence to Gemini or Ollama. Verified citations are constructed locally.

Retrieved documents are untrusted reference material and cannot alter the generation instructions.

The default hash embedding is deterministic and offline. A local sentence-transformers model can be enabled explicitly without changing the storage contract.
