# Note di rilascio — v0.4.5 (prima release autonoma della fork)

**Data:** 17 settembre 2026 · **Gioco:** Aniimo Steam, update `3544783` (invariato)

## Novità

- **Tutto gestito da questa repo.** Rimosso il monitoraggio delle release a monte: le novità riguardano esclusivamente `notorious-pizza/Aniimo-Italian-Translation`, che da ora pubblica i propri eseguibili.
- **Due eseguibili precompilati** (non serve Python):
  - `Aniimo-Centro-Controllo.exe` — il Centro di controllo grafico: stato a colpo d'occhio (gioco, installazione, allineamento patch, novità), applica traduzione e ripristina backup con un clic, mascotte animata e musichetta sintetizzata.
  - `Aniimo-Italian-Translation.exe` — l'installer classico a menu testuale, invariato nel funzionamento.
- **Fix «Controllo offline» errato**: il limite orario dell'API GitHub (403) e l'assenza di release (404) non vengono più etichettati come «GitHub non raggiungibile». Fallback via pagina web non soggetta al limite, cache del controllo (30 min), orario dell'ultimo controllo mostrato nella card Novità.
- Testi della traduzione invariati rispetto alla v0.4.3 (audit indipendente superato).

## Installazione

- **GUI**: apri `Aniimo-Centro-Controllo.exe` → «✦ Applica traduzione» → nel gioco seleziona **Inglese**.
- **Installer testuale**: apri `Aniimo-Italian-Translation.exe` e premi Invio.

Il backup automatico viene creato sempre; il ripristino è immediato (opzione 2 nell'installer, pulsante ♻ nella GUI).

## Attribuzione

Traduzione originale di [Sici29](https://github.com/Sici29) (MIT). Questa fork aggiunge l'audit indipendente di fedeltà, le correzioni terminologiche, il Centro di controllo grafico e la manutenzione autonoma.
