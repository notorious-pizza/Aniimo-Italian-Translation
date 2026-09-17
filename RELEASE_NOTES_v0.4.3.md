# Note di rilascio — v0.4.3 (fork notorious-pizza)

**Data:** 17 settembre 2026 · **Gioco:** Aniimo Steam, update `3544783` (invariato rispetto alla v0.4.2)

## Novità

- **Audit indipendente di fedeltà superato.** Tutte le 112.187 chiavi sono state verificate contro le stringhe inglesi reali estratte dall'archivio di localizzazione del gioco: pairing SHA-256 perfetto, fingerprint di build combaciante, 0 violazioni di placeholder/tag/newline, 0 residui di inglese e 0 errori di significato nel campione stratificato di 324 coppie. Dettagli in [`AUDIT_FIDELITA_v0.4.2.md`](AUDIT_FIDELITA_v0.4.2.md).
- **3 correzioni terminologiche applicate** (unica modifica al testo rispetto alla v0.4.2):
  - `1090869768`, `2068081817`: "Dipartimento Arte della Battaglia" → "Dipartimento Arti da Battaglia" (allineato alla forma usata nelle altre 13 occorrenze).
  - `1799612016`: "La Shelly derubata" → "Lo Shelly derubato" (allineato alle 14 occorrenze maschili dello stesso NPC).
- **Strumenti di audit pubblicati** in `tools/audit/`: riutilizzabili dopo ogni aggiornamento del gioco per verificare copertura, pairing e qualità prima di rilasciare.

## Installazione

Invariata rispetto alla v0.4.2: chiudi Aniimo e il launcher, apri l'installer, premi Invio, seleziona **Inglese** nel gioco. Il backup automatico e il ripristino (opzione 2) funzionano come prima.

## Attribuzione

Traduzione originale di [Sici29](https://github.com/Sici29) (MIT). Questa fork aggiunge l'audit indipendente di fedeltà, le correzioni elencate e la manutenzione da parte di notorious-pizza.
