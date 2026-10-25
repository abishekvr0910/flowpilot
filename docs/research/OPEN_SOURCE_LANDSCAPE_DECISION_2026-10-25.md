# Open-source / data-openness landscape — decision record (2026-10-25)

Regenerated from the 2026-10-23 recon (the earlier draft was lost in the
fa524f6 repository-cleanup wave). Written offline; facts are from the recorded
recon, not re-fetched.

## Recon digest (2026-10-23 sources: githubtrending.today, swen.live, product pages)

Three overlapping waves on GitHub trending, October 2026:
1. **Agent/skills wave** — cloudflare/security-audit-skill #1 today (+2.9k/day,
   40.6k★); knowledge-work-plugins 31.9k★; NVIDIA/OpenShell 18.2k★. Openness here
   is *protocol* (standard skills, runtimes, machine-readable findings).
2. **Local-first AI wave** — VoiceStudio (solo founder, local ElevenLabs
   alternative, 646 languages, AGPL-3.0): 80.8k★, +46.6k/month (+136%). The pitch
   is ownership ("your voice never goes to someone's cloud").
3. **Data-access wave** — Agent-Reach (+148/day, "zero API fees"), firecrawl,
   crawl4ai.

## How the data-openness products were initiated (template)

| Case | Lever | Initiation |
|---|---|---|
| Airbyte | community for the long tail | YC W20 "pre-idea" → interview-transcribed pain → MVP = 6 connectors (Sept 2020) → LinkedIn/email soft launch → open-core after proof ($181M raised) |
| OpenAlex | CC0 data + governance | nonprofit from a 2011 hackathon → launched Jan 3, 2022 into the Microsoft Academic Graph vacuum → freemium tools fund free data (POSI-governed) |
| OLMo / Ai2 | endowment + $152M NSF grant | "fully open" = weights+data+code+evals; reproducibility as brand (Google reproduced training on TPUs) |
| CKAN | boring-default utility | NGO infra project → 20 years → de-facto gov portal standard |
| VoiceStudio | solo builder, ownership bet | one-sentence claim ("the open local ElevenLabs") → AGPL + opt-in consent analytics → product-as-distribution, +46k★/month |

Shared sequence: named insider pain → one-sentence "open X" claim → tiny
high-quality MVP → openness chosen for a structural reason → launch into an
existing channel → monetization edge added only after community proof.

## Decision (2026-10-25)

- **Direction A seeded with a C artifact**: narrow local-first open tool in the
  wave VoiceStudio validated, launched with a small CC0 benchmark artifact.
- **Wedge chosen**: **transcript cleaner** — the open, fully-local transcript
  cleaner; the editing layer any ASR can use.
- Scaffolded (offline, no remote, no push):
  `S:\APPs\transcript-cleaner\` — README (position line), LICENSE
  (MIT; swap to AGPL-3.0 before public showcase if the SaaS-loophole argument
  matters), pyproject.toml with `tclean` console script, .gitignore, spec.md
  (v0.1 slice + done-when incl. CC0 benchmark artifact).
