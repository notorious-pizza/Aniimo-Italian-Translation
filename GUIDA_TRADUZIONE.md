# Brief di traduzione — ANIIMO italiano (per umani e agenti AI)

Regole applicate dall'audit di fedeltà v0.4.2 (112.187 stringhe, 0 errori di significato).
Leggile tutte prima di tradurre una sola riga.

## Terminologia fissa (glossario)

| Inglese | Italiano |
|---|---|
| Pathfinder | Esploratore |
| HP / EP | PV / EP |
| RV | camper |
| Home | Base |
| Twine / twining | Sincronia / sincronizzarsi |
| Outpost | Avamposto |
| Institute / Polaris Institute | Istituto / Polaris Institute (nome proprio) |
| Sanctum | Santuario |
| Chest | Forziere |
| Hatchinator | Hatchinator (invariato) |
| Alpha | Alpha (invariato) |
| BREAK (meccanica) | BREAK (invariato) |
| REGEN | RIGEN |
| Placeholder / reserved | Segnaposto / riservato |
| Battle Art Department | Dipartimento Arti da Battaglia (MAI "Arte della Battaglia") |
| Companion Handbook | Manuale Compagni |
| Training Coins | Monete Allenamento |
| Dewdrop Crystals | Cristalli di Rugiada |
| Energy Amber | Ambra Energetica |
| Lumin Stage / Nova Stage | Fase Lumin / Stadio Nova |

**Nomi propri di creature, luoghi, festival e marchi RESTANO IN INGLESE**: Bolty, Shelly,
Mistwoods, Beast Fang Ridge, Russet Highlands, Lost Isles, Bloomville, Astra, GoGoHomes,
Morning Blossom Festival, GoGo… (plurali inglesi anche: "i Bolties" ok come "i Bolty").
Eccezione storica documentata: il collezionabile "Muyu" è reso "[Piuma Baciata dalla Luce]".

## Formato e markup — VIETATO ROMPERE

- Placeholder `{0}` `{1}` `{n}` `%d` `%s`: stessi token, stesso ordine di significato.
- Tag rich-text: `<style=…></style>`, `<color=#…></color>`, `<sprite name="…">`,
  `<link="…"><u>…</u></link>`, `<BR>` — copiali identici; traduci SOLO il testo visibile.
- Tasti: `#kHud/NormalAttack#z`, `#playerName#` — invariati.
- Etichette tra quadre che sono TESTO si traducono: `[New]`→`[Nuovo]`, `[Defense]`→`[Difesa]`;
  quelle che sono MECCANICHE restano: `[BREAK]`.
- Ritorni a capo (`\n` nei campi CSV): stesso numero.
- Virgolette del CSV: il campo viene riscritto con csv module, non aggiungere virgolette a mano.

## Stile

- Italiano di gioco vivo e pulito; registro giovanile per NPC giovani, tecnico per tooltip.
- Frasi brevi per UI; niente riempitivi. "You" → tu.
- Punteggiatura italiana; ellissi sempre "..." (tre punti); trattino lungo "—" per pause.
- Genere: maschile di default generico; NPC noto usa il suo genere (Esploratrice Lita).
- NON inventare contenuti. Se l'inglese è un segnaposto di sviluppo ("placeholder",
  testo ripetuto), traduzione letterale minima.
- Date testuali in GG/MM/AAAA quando ricompate.

## Procedura operativa (flusso autonomo completo)

1. `python tools/aggiorna_traduzione.py estrai [--game-dir …]`
   → `data/da_tradurre_<build>.csv` con le stringhe nuove/modificate.
2. Traduci riempiendo SOLO la colonna `it` (a mano o con agenti AI usando questo brief;
   con agenti: dividere in batch da ~200 righe, un agente per batch, in parallelo).
3. `python tools/aggiorna_traduzione.py unisci --file data/da_tradurre_<build>.csv --versione X.Y.Z`
   → fonde nel CSV principale e aggiorna manifest (chiavi, fingerprint, build, versione).
4. `python tools/aggiorna_traduzione.py verifica` → deve dire "PERFETTO".
5. `python -m pytest tests/ -q` verde → commit & push.
6. `python tools/pubblica_release.py --titolo "…" --note file.md` → builda entrambi gli EXE,
   li collauda e pubblica la release GitHub (attesa propagazione inclusa).
7. Riapplica la traduzione dal Centro di controllo (l'update del gioco l'ha riportata in inglese).

Nota: dopo un update del gioco, le copie non ancora aggiornate (es. launcher più vecchio)
possono mostrare avvisi di stringhe non verificate finché non ricevano la stessa patch.
