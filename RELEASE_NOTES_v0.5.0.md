# Note di rilascio — v0.5.0 (build 3584014)

**Data:** 20 settembre 2026 · **Gioco:** Aniimo Steam, update `3584014`

## Novità

- **Traduzione allineata alla patch 3584014**: 837 stringhe tradotte (111 nuove + 726 modificate da NetEase), 91 chiavi rimosse dal gioco potate dal catalogo — copertura 112.207/112.207 (100%).
- Traduzione delle nuove stringhe eseguita in parallelo da quattro agenti AI seguendo il brief di stile del progetto (`GUIDA_TRADUZIONE.md`), con verifica automatica di pairing e formato.
- **Nuovo kit di aggiornamento autonomo**:
  - `tools/aggiorna_traduzione.py` — `estrai` (esporta le stringhe nuove/modificate dal gioco), `unisci` (fonde le traduzioni e aggiorna il manifest), `verifica` (copertura + pairing).
  - `tools/pubblica_release.py` — builda entrambi gli EXE, li collauda e pubblica la release GitHub in un comando.
  - `GUIDA_TRADUZIONE.md` — brief di stile completo (glossario, regole markup, procedura end-to-end): umani e agenti AI possono aggiornare la traduzione in autonomia a ogni patch.
- Nota per le copie non aggiornate (es. launcher ancora alla 3544783): le chiavi rimosse/ritoccate degradano con fallback inglese finché anche quella copia non riceve la patch.

## Installazione

Invariata: chiudi Aniimo e il launcher, apri il Centro di controllo (o l'installer), applica, nel gioco seleziona **Inglese**. Backup automatico sempre creato; ripristino immediato. ⚠ Traduzione non ufficiale per gioco always-online con anti-cheat: nessuna garanzia contro sanzioni.
