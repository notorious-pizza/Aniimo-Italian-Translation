# Audit indipendente di fedeltà — traduzione italiana v0.4.2

**Data audit:** 17 settembre 2026
**Target:** `data/translation_it.csv` (v0.4.2, 112.187 chiavi)
**Gioco verificato:** Aniimo Steam, update **3544783**, revisione `dbb6cb6c4a6308e6c8796ce22cae6952` (installazione locale reale)
**Metodo:** confronto diretto con le stringhe inglesi originali estratte dall'archivio di localizzazione del gioco (`Aniimo_Data/cvs/res/lua/LuaScripts.xdf` → `NewTextMap_en.json` + `Compress_en.bin`), senza basarsi sulle dichiarazioni del progetto originale.

Questo audit è stato eseguito su una copia indipendente (**fork**) della traduzione [Sici29/Aniimo-Italian-Translation](https://github.com/Sici29/Aniimo-Italian-Translation), di cui questa repo è derivata con attribuzione MIT.

---

## 1. Verdetto sintetico

| Area | Esito |
|---|---|
| Copertura chiavi | **112.187 / 112.187 (100%)** — 0 mancanti, 0 extra |
| Fingerprint build | **Combacia** (`a9d7e25b…` dichiarato = calcolato sul gioco locale) |
| Pairing per chiave (SHA-256 dell'inglese sorgente) | **112.187 / 112.187 (100%)** — ogni stringa IT deriva dall'inglese esatto della build |
| Placeholder `{0}`/`{1}`/… | **0 violazioni** su tutte le stringhe |
| Newline e spazi di bordo | **0 violazioni** |
| Residui di inglese non tradotto | **0** (0 stringhe lunghe con ≥2 parole inglesi comuni residue) |
| Tag funzionali `<style>`/`<size>`/`<color>`/`<sprite>`/`<link>` | **11 deviazioni, tutte deliberate e sicure** (dettaglio §4) |
| Fedeltà semantica (campione 324 coppie stratificate) | **0 errori di significato**; 6 anomalie minori (1,9%), di cui 3 corrette in questa fork |
| Stringhe identiche EN=IT | 13.434, di cui 9.719 parole singole (nomi propri), 32 testi lunghi **tutti** legittimamente non traducibili (sprite, onomatopee, segnaposto di test) |

**Conclusione: la traduzione è fedele all'originale e di qualità professionale. L'italiano è idiomomatico, coerente con un glossario interno (Esploratori=Pathfinders, PV=HP, camper=RV, Sincronia=Twine, Segnaposto=Placeholder…) e preserva integralmente markup e segnaposto.**

## 2. Copertura e pairing

- Chiavi del gioco (slot inglese): **112.187**; righe CSV: **112.187**; intersezione perfetta.
- `sha256(sorted(keys))` del gioco locale = `a9d7e25ba08e05a68267cedd4aac9d37b693c4648d8d22224d69251113b4a514` = fingerprint dichiarato in `supported_versions.json` → il CSV è costruito **esattamente** per questa build.
- Per ogni chiave, `sha256(testo inglese del gioco)` = `source_sha256` del CSV: **0 mismatch**. Il CSV non ridistribuisce l'inglese originale, ma l'hash per chiave dimostra il pairing.

## 3. Campione stratificato (324 coppie, seed fisso 20260917)

Strati: A_ui_corta (70) · B_media (90) · C_dialogo (70) · D_lunga (40) · E_identica_lunga (32) · segnalazioni automatiche (22).
File campione: `data/audit_fidelity_sample_v0.4.2.jsonl`.

Risultati della revisione manuale EN→IT:

- **Errori di significato: 0.** Nessuna stringa cambia informazione di gioco (valori, meccaniche, nomi, condizioni).
- Qualità stilistica elevata: dialoghi naturali, registro adatto (giovanilistico per NPC giovani, tecnico per tooltip di abilità), adattamenti creativi appropriati (es. gioco di parole EN "imp/Wimp" → IT "ardo/codardo", chiave 2109741675).
- Anomalie minori riscontrate (6 su 324, 1,9%):

| Chiave | Problema | Gravità | Esito |
|---|---|---|---|
| 2068081817 | "Dipartimento Arte della Battaglia" vs forma dominante "Dipartimento Arti da Battaglia" (13 occorrenze) | minore | **Corretta** in questa fork |
| 1090869768 | idem | minore | **Corretta** in questa fork |
| 1799612016 | "La Shelly derubata" vs maschile usato nelle altre 14 occorrenze dello stesso NPC | minore | **Corretta** in questa fork |
| 2047945200 | "Dear Pathfinder," reso "Salve," (vocativo omesso) | cosmetica | Lasciata (registro accettabile per notifica di moderazione) |
| 1233663597 | "I Bolty lo adorano" — elisione "l'adorano" preferibile | cosmetica | Lasciata (grammaticalmente valida) |
| 1947121834 | "[Muyu: Floating Light]" reso "[Piuma Baciata dalla Luce]" — nome proprio interamente tradotto | scelta di localizzazione | Lasciata (coerente su tutto il corpus, 0 residui "Muyu") |

## 4. Tag funzionali (11 deviazioni su 112.187)

Tutte verificate una per una (`data/audit_tag_issues_v0.4.2.json`):

- 8× `Free` → `<size=-6>Gratis</size>` (tag aggiunti di proposito per il corpo piccolo; sintassi Unity valida, applicata in modo uniforme).
- 1× `<Twenty>` → `<Vent'anni>` (marcatore narrativo di parola-chiave, sintassi preservata).
- 1× `<Title Name (Placeholder) Title>` → tradotto (segnaposto di sviluppo).
- 1× `Tab<占位>` → `Scheda<segnaposto>` (marcatore cinese di segnaposto reso in italiano).

Nessun tag di rendering è stato perso o rotto. I 755 "mismatch" dell'analisi grezza con parentesi quadte erano falsi positivi: etichette UI tipo `[New]`→`[Nuovo]`, `[Defense]`→`[Difesa]` correttamente tradotte.

## 5. Outlier di lunghezza (7 su 112.187)

Tutti su stringhe-segnaposto di sviluppo con testo ripetuto/garbage (es. "Streamer signature placeholder" ripetuto 6 volte, "A paintingA painting…"), condensate in italiano in forma sensata. Nessuna stringa di gioco reale coinvolta.

## 6. Rischi e integrità (verifica locale)

- Il gioco verifica l'integrità dei file del pacchetto base tramite `md5list.txt` (2.102 voci, tutte sotto `worldx_Data/StreamingAssets/cvs/`): **l'archivio patchato dall'installer (`Aniimo_Data/cvs/res/lua/LuaScripts.xdf`, overlay hot-update) non è in quella lista** e il file `verify/DefaultPackage_verify.txt` dell'overlay contiene solo un numero di versione, non hash dei file Lua.
- Restano validi gli avvertimenti del progetto originale: anti-cheat NetEase (NEP2.dll + driver kernel), servizio sempre online; **nessuna garanzia contro controlli lato server o sanzioni all'account**; il backup ripristina i file ma non protegge da eventuali provvedimenti. L'installazione è a proprio rischio.

## 7. Strumenti

Gli script dell'audit sono in `tools/audit/` e sono riutilizzabili dopo ogni update del gioco:

- `audit_coverage.py` — copertura chiavi, fingerprint build, pairing SHA-256.
- `audit_fidelity.py` — controlli automatici globali (placeholder, tag, newline, bordi, lunghezze, residui EN) e generazione campione stratificato.
- `audit_terms.py` — verifica mirata di varianti terminologiche.
- `apply_fidelity_fixes.py` — applicazione delle correzioni del §3 (idempotente).
