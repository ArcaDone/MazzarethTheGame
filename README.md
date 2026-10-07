# Mazzarino 80

Gioco open world nello stile di GTA e Red Dead Redemption 2, ambientato a **Mazzarino (Caltanissetta) negli anni '80**. Il paese è ricostruito sui dati reali: terreno, strade ed edifici di OpenStreetMap. Le case sono generate in modo procedurale con lo stile delle case siciliane dell'entroterra.

Progetto Unreal Engine **5.5**: `MazzarethTheGame.uproject`, nato dal Game Animation Sample.
Repository privato: `ArcaDone/MazzarethTheGame` (Git + LFS).

- **Dove si va:** [`Research/Mazzarino80/PIANO_GTA.md`](Research/Mazzarino80/PIANO_GTA.md) (fasi, traguardi, cosa è fatto e cosa manca).
- **Dove siamo:** questo file.

---

## 1. Aprire il progetto

| Cosa | Dove |
|---|---|
| Motore | Unreal 5.5 in `D:\UE_5.5` |
| Compilare (editor chiuso) | `D:\UE_5.5\Engine\Build\BatchFiles\Build.bat MazzarethTheGameEditor Win64 Development -Project="D:\UE5Projects\GameAnimationSample\MazzarethTheGame.uproject"` |
| Mappa d'apertura | `/Game/Levels/Main`: vuota, si apre in pochi secondi |
| **Mappa del paese** | `/Game/Mazzarino80/Houses/Maps/L_M80_Paese_WP` (World Partition) |
| Modalità di gioco | "Mazzarino 80 (gioco)" (`M80GameMode`), predefinita del progetto |

**La mappa del paese è in World Partition.**
- Ogni attore (casa, strada, lampione…) è un file a sé in `Content/__ExternalActors__/…/L_M80_Paese_WP`.
- La mappa si apre vuota in 3 secondi.
- Per lavorare su una zona: finestra *World Partition* → selezioni le celle → *Load Region from Selection*. Caricare i 250 m intorno al Corso richiede circa 50 secondi; tutto il paese pesa molto di più.
- Atmosfera, orizzonte e zone di esclusione sono sempre caricati.
- In gioco le zone si caricano da sole intorno al giocatore. Da lontano si vedono gli **HLOD**: versioni semplificate delle case.
  - Si ricostruiscono con il comando qui sotto (circa 35 minuti, editor chiuso).
  - **Non si versionano** (oltre 700 MB a ogni ricostruzione): restano in locale e nel backup.
  - I loro file sono elencati in `.git/info/exclude`.

```
"D:\UE_5.5\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "D:\UE5Projects\GameAnimationSample\MazzarethTheGame.uproject" /Game/Mazzarino80/Houses/Maps/L_M80_Paese_WP -run=WorldPartitionBuilderCommandlet -Builder=WorldPartitionHLODsBuilder -AllowCommandletRendering
```

Altre mappe:
- `Houses/Maps/L_M80_Houses18_V2`: 18 case di prova del generatore.
- `Vehicles/L_M80_ProvaGuida`: pista di prova delle auto (rettilineo, rampe, slalom, vicolo). Tab cambia auto.
- `Rooms/L_M80_RoomStudio`: le stanze fotografate per le finestre.
- `L_M80_District_V2`: quartiere di prova, solo in locale.

---

## 2. Com'è fatto

### Plugin (C++, in `Plugins/`)

| Plugin | Contenuto |
|---|---|
| `MazzarinoHouses` | Generatore delle case e attrezzi per il paese |
| `MazzarinoRoads` | Strade a spline (dati OSM) e vecchi edifici a perimetro |
| `MazzarinoVehicles` | Auto Chaos guidabili, livello e GameMode di prova guida |
| `MazzarinoGameplay` | Giocatore, HUD, armi, vita, atmosfera, orizzonte, lampioni |

### Attori da trascinare nella mappa (Place Actors, cerca il nome)

| Nome | A cosa serve |
|---|---|
| **Casa Mazzarino (procedurale)** | Una casa o una schiera su un perimetro a spline chiusa. Il pannello *Casa* ha stile, piani, finitura, degrado, tetto, schiera, terreno, "Vissuto", negozi e bar per lato, dettagli siciliani. Pulsanti *Rigenera* e *Rigenera con i vicini*. |
| **Isolato da riempire** | Disegni il perimetro di un isolato con una spline chiusa e premi *Genera case*: crea una schiera tutto intorno con un cortile al centro (profondità, piani, stile, seed). *Elimina case generate* le toglie. Serve per riempire le zone dove OSM non ha case. |
| **Zona senza case procedurali** | Perimetro a spline: le case con il centro dentro spariscono, per lasciare posto agli edifici fatti a mano (Matrice, Comune, Poste…). Spegnendo o spostando la zona le case tornano. |
| **Strada Mazzarino (spline)** | Strade OSM (1016): larghezza, quote, pavimentazione. Sul landscape le strade sono dipinte (layer "Strada"); le spline servono da guida a case, marciapiedi e lampioni. |
| **Marciapiede** | Spline con lastra e cordolo in pietra lavica: aperto, ad anello o piazza piena. |
| **Scalinata** | Spline per gradini, cordonate e scalinate (anche in curva, in salita o in discesa) in pietra lavica e basolato, piene fino a terra o a soletta, con pianerottoli, muri laterali e staccionate (ferro battuto, tubolare, legno, canne). Prova: `L_M80_ProvaScalinate` (`Scripts/m80_stairs_setup.py`). |
| **Strada (Mazzarino)** | Spline per strade che si appoggiano al terreno come i marciapiedi e si inclinano di lato col pendio. *Superficie*: Lavica principale (`LowPoly`), Lavica bombata (`Lavica_curved`), Lastra con materiale (default `MI_M80_Lavica_secondaria`, mappata in metri) o mesh personalizzata. Le mesh si ripetono a pezzi proporzionati. Prova: `L_M80_ProvaScalinate`, cartella *Strade* (`Scripts/m80_road_setup.py`). |
| **Fili tra le case** | Cavi elettrici che attraversano la strada tra case vicine. |
| **Lampione (Mazzarino)** | Tipo *Muro* (lanterna esagonale a braccio) o *Palo* (candelabro in ghisa a tre luci). Modellati in Blender dalle foto dei lampioni veri. Si accendono da soli al tramonto. Opzioni *Spento (guasto)* e *Modello* per cambiare mesh. |
| **Atmosfera (Mazzarino)** | Sole nella posizione reale per Mazzarino (latitudine, giorno dell'anno, ora), luna, cielo, nuvole, foschia nelle valli, ora blu, notte. Meteo: Sereno, Afa estiva, Scirocco, Nuvoloso. In gioco l'ora avanza. |
| **Orizzonte (colline ed Etna)** | Anello di colline lontane con il profilo dell'Etna. |
| **Auto Mazzarino** | Fiat 126, Ape, Panda, 127, Uno, Golf GTI, Vespa. |

### Le case
- Ogni casa è una mesh generata dal C++ (anteprima live).
- Per la versione finale si **cuoce** in una Static Mesh Nanite, con `Scripts/m80_houses_bake.py`. Le mesh cotte vanno in `Content/Mazzarino80/Houses/Baked/…`: circa 900 MB, **fuori da Git**, si rigenerano.
- Qualsiasi modifica riporta la casa in anteprima finché non la ricuoci.
- **Stili** (`Content/Mazzarino80/Houses/Styles`):
  - 01 popolare in pietra
  - 02 palazzo urbano
  - 03 intonacata anni '50-'70
  - 04 casa povera

  Ogni stile contiene materiali, regole di facciata, liste di piante e oggetti.
- **Master material** `M_M80_HouseMaster`: texture senza ripetizioni (hex tiling), macchie, colature, umidità di risalita, intonaco che cade, muschio, palette di colori per casa.
- **Dettagli:**
  - piante, vasi, antenne, cisterne, panni stesi;
  - capochiave, tende a listarelle, case abbandonate;
  - ceramiche siciliane: teste di moro, pigne, graste, edicole votive, numeri civici;
  - targhe con i nomi veri delle vie, cartelli stradali, manifesti d'epoca.

  Sono istanze leggere, senza collisione, che spariscono oltre i 60 m (le piante oltre i 90 m).
- **Finestre con stanze in parallasse:** cucine, camere, negozi e bar fotografati in cubemap, accesi di notte.
- Oltre alle case procedurali il paese ha edifici fatti a mano: Matrice, Comune, palazzi neoclassici e le Poste importate da Blender.

### Cartelle utili

| Cartella | Contenuto |
|---|---|
| `Content/Mazzarino80/Houses` | Mappe, stili, materiali e mesh cotte delle case |
| `Content/Mazzarino80/Kit` | Oggetti versionati: piante, cartelli, ceramiche siciliane, lampioni, marciapiedi |
| `Content/Mazzarino80/Vehicles`, `Player`, `Weapons`, `UI`, `Sky`, `Audio` | Gioco |
| `Scripts/` | Automazione dell'editor (Python) |
| `Tools/` | Backup, mappa del radar, suoni, migrazione dal progetto Comune |
| `Research/Mazzarino80/` | Dati OSM, terreno, piani, script Blender (`Blender/`) |

`Megapack`, `Megascans`, `Migrated` e gli altri pacchetti del marketplace sono **fuori da Git**: sono nel backup e nel progetto `D:\UE5Projects\Comune`.

---

## 3. Script di automazione

Gli script Python girano in un editor lanciato apposta:

```
powershell -ExecutionPolicy Bypass -File Scripts/run_editor_script.ps1 -Script Scripts/<script>.py [-ForceLit]
```

- **Mai con l'editor già aperto:** due editor sul paese esauriscono gli 8 GB della scheda video.
- `-ForceLit` serve per le foto: se lasci la vista in *Unlit*, la mette in *Lit* durante lo script e poi la rimette com'era.
- Nella mappa World Partition gli script caricano solo la zona che serve, a riquadri. Gli aiuti stanno in `Scripts/m80_seq.py` (`actor_descs`, `load`, `tiles`, `save_all`).
- I report finiscono in `Saved/Mazzarino80/…`, le foto in `Saved/Mazzarino80/Foto`.

| Script | Cosa fa |
|---|---|
| `m80_houses_bake.py` | Cuoce le case non ancora cotte, riquadro per riquadro. Report con le case fallite. |
| `m80_houses_district.py` | Crea le case dai lotti OSM, saltando quelli coperti da edifici fatti a mano. |
| `m80_town_zones.py` | Zone di esclusione attorno agli edifici fatti a mano, sul loro perimetro reale visto dall'alto (`m80_footprints.py`). |
| `m80_town_roads.py`, `m80_town_sidewalks.py`, `m80_town_props.py` | Strade dipinte, marciapiedi, cartelli e manifesti. |
| `m80_signs_setup.py`, `m80_street_wires_setup.py` | Targhe delle vie e cartelli; fili tra le case. |
| `m80_town_streetlights.py` | Lampioni a muro ogni 28 m lungo le strade, a lati alterni, il 5% guasti. |
| `m80_atmosphere_setup.py` | Piazza Atmosfera e Orizzonte. |
| `m80_atmosphere_photos.py`, `m80_town_aerial.py`, `m80_photos.py` | Foto a ore e meteo diversi; viste aeree. |
| `m80_profile_scene.py` | Misura fps, GPU, draw call e tempo di caricamento. |
| `m80_props_nanite.py`, `m80_town_hlod_setup.py` | Nanite sui dettagli; impostazione degli HLOD. |
| `m80_lamps_setup.py`, `m80_sicilia_setup.py`, `m80_import_blender_assets.py` | Import dei modelli da Blender (lampioni, ceramiche, edifici, veicoli). |
| `m80_play_test.py`, `m80_weapons_test.py`, `m80_vitals_test.py`, `m80_drive_telemetry.py`, `m80_cars_damage_test.py` | Test automatici in gioco con foto e report. |

I circa 220 script `mazzarino80_*.py` sono della prima versione basata su PCG (settembre 2026): restano solo come archivio e non servono più.

### Modelli da Blender
- Gli script stanno in `Research/Mazzarino80/Blender/`. Producono FBX e texture dipinte o cotte con Cycles: lampioni, ceramiche siciliane, cartelli, armi, occhiali, tuta.
- Si lanciano con `blender -b --factory-startup --python <script>.py`.
- Poi si importano in Unreal con lo script `m80_*_setup.py` corrispondente.
- **Veicoli:** `m80_prepare_vehicle.py` + `m80_import_blender_assets.py`. Vanno rispettati i nomi delle ossa delle ruote, l'orientamento e la scala in cm, altrimenti Chaos si rompe.

---

## 4. Git e LFS

- Commit piccoli, uno per argomento, con push uno alla volta. In `git add` vanno sempre i percorsi espliciti, mai `commit -a`.
- La quota LFS gratuita è di **10 GB**: oggi ne usiamo circa 5,7.
- Della mappa del paese si versionano solo i file degli attori cambiati.
- Sono **fuori da Git**:
  - le mesh cotte delle case;
  - gli HLOD;
  - i pacchetti del marketplace;
  - l'Ape (324 MB);
  - `Saved`, `Intermediate`, `DerivedDataCache`, `Binaries`.
- La vecchia storia (95 commit, fino al 4 ottobre 2026) è in `.git_old`: 38 GB, solo in locale.

---

## 5. Backup e trasferimento su un altro PC

Script: `Tools/Backup/MTGBackup.ps1`.

### Backup giornaliero
- L'attività pianificata di Windows **MTGBackup** lo lancia ogni giorno alle 13:00 e copia tutto in `C:\MTGBackup`.
- Copia solo i file nuovi o cambiati e **non cancella mai nulla**: un file eliminato per sbaglio su D: resta recuperabile qui.
- Cosa copia:
  - il progetto, senza `.git`, cache, `Binaries` e `Intermediate`;
  - `Saved/Autosaves` e `Saved/Mazzarino80` (report, foto, copie delle mappe);
  - il progetto `D:\UE5Projects\Comune`;
  - i sorgenti Blender in `D:\Blender\AssetsMazzarethTheGame`;
  - le foto di riferimento e i lavori Blender in `D:\BlenderTest`, più le immagini ricevute in chat (in `Saved/Mazzarino80/Riferimenti`);
  - `D:\HDRI` e `D:\Audio_Music`;
  - gli appunti di Claude Code sul progetto (in `ClaudeMemory`, da rimettere in `C:\Users\<utente>\.claude\projects\D--UE5Projects-GameAnimationSample\memory`).
- Lanciarlo a mano (meglio con l'editor chiuso):
  ```
  schtasks /Run /TN MTGBackup
  ```
- Su un disco esterno:
  ```
  powershell -ExecutionPolicy Bypass -File Tools\Backup\MTGBackup.ps1 -Dest E:\MTGBackup
  ```
- I log stanno in `<destinazione>\_logs`. Ogni log finisce con `FINISHED … - OK` oppure `WITH ERRORS`.

**Attenzione:** il backup giornaliero conserva anche i file cancellati, quindi **non va usato per spostare il progetto**. Con World Partition, gli attori eliminati ricomparirebbero nella mappa come doppioni.

### Copia per trasferimento (`-Transfer`)
Una copia pulita, identica a D:, da portare su un altro PC:

```
powershell -ExecutionPolicy Bypass -File Tools\Backup\MTGBackup.ps1 -Transfer -Dest E:\MTGBackup
```

- Scrive in `<Dest>\Trasferimento\` con la stessa struttura di D:
  - `UE5Projects\GameAnimationSample`
  - `UE5Projects\Comune`
  - `Blender\AssetsMazzarethTheGame`
- È uno **specchio**: quello che non c'è più su D: viene tolto anche dalla copia (solo dentro `Trasferimento`). Le volte successive copia solo le differenze.
- Include `.git` con i file LFS (circa 5,4 GB): sull'altro PC il repository funziona subito, senza clonare.
- Include anche le **Binaries** già compilate dei plugin.
- Esclude cache, `Intermediate`, `Saved` e `.git_old`.
- Se l'editor è aperto si rifiuta di partire. Il log è `_logs\transfer_<data>.log`.
- Peso indicativo: circa 45 GB il progetto e circa 100 GB il progetto Comune.

Sull'altro PC:
1. Copia `UE5Projects` e `Blender` nella radice di **D:**, così tornano gli stessi percorsi di qui.
2. Installa Unreal **5.5**, possibilmente in `D:\UE_5.5`, e Git con Git LFS.
3. Apri `MazzarethTheGame.uproject`.
   - Con le Binaries incluse e lo stesso Unreal 5.5 si apre senza compilare.
   - Se chiede di ricompilare i moduli serve **Visual Studio 2022** con "Sviluppo di giochi con C++".
4. La prima apertura è lenta, da una a qualche ora: ricompila gli shader. Poi va normale.
5. Per rifare gli HLOD usa il comando del capitolo 1.

---

## 6. Cosa abbiamo fatto (in breve)

| Periodo | Lavoro |
|---|---|
| 27-28 set 2026 | Terreno reale (Copernicus 30 m), strade OSM a spline, città ribaltata sull'asse Y per farla combaciare col posto. Prima versione delle case con PCG (18 case campione), poi abbandonata. |
| 1-2 ott | Generatore di case **V2** in C++ (plugin `MazzarinoHouses`) con stili e master material. **V3 "vissuto" alla RDR2**: piante, antenne, fili, terrazzi, cortili, scale, negozi e bar, stanze in parallasse, case abbandonate, cartelli e targhe, ceramiche siciliane. |
| 3 ott | Paese `L_M80_Paese` con tutte le case cotte; edifici fatti a mano con zone di esclusione; strade dipinte, marciapiedi, manifesti, palazzi neoclassici. Auto guidabili (Chaos), pista di prova, giocatore MetaHuman in tuta acetata, HUD con radar. |
| 4 ott | Terreno ritoccato a mano. Storia Git azzerata (repository nuovo, circa 4,9 GB di LFS). Piano GTA. Armi, vita e morte, danni e fuoco delle auto, 7 veicoli. |
| 6 ott | Tutti i lotti OSM; zone sui perimetri reali degli edifici fatti a mano; strumento **Isolato da riempire**. **Atmosfera** con sole reale, notte, ora blu e Etna all'orizzonte. **World Partition** (la mappa si apre in 3 s invece che in 5 minuti), dettagli più leggeri, Nanite, HLOD. **Lampioni** dalle foto vere: 941 a muro. Backup con copia per trasferimento. |

---

## 7. Punti aperti

- **Macchia nel cielo** nelle viste aeree molto alte: sembra un difetto delle nuvole, non dell'orizzonte. Ancora da capire.
- **Poste**: alcune lamelle della facciata sono storte già nel modello originale. Vanno sistemate a mano in Blender e reimportate.
- **Zona delle Salesiane**: OSM non ha case nel triangolo. Si riempie a mano con *Isolato da riempire*.
- **Candelabri a tre luci**: da piazzare a mano nelle piazze.
- Due "case" OSM (lotti 1249067262 e 1249081252) sono triangoli di 0,6 m²: errori dei dati, non generano nulla.
- Il vaso `SM_M80_PROP__PottedPlant_Small_01` risulta modificato in locale da prima del 6 ottobre: decidere se tenerlo.
- `.git_old` (38 GB) va spostato o cancellato quando non serve più.

## 8. Fonti e licenze

- Edifici, strade e chiese: © contributori **OpenStreetMap**, licenza ODbL (`Research/Mazzarino80/Mazzarino_OSM_*`). Va citato nei materiali distribuiti. Sono dati di oggi, non del 1980.
- Terreno: Copernicus GLO-30 (`Copernicus_GLO30_N37_E014.tif`).
- Per gli anni '80 servono le fonti datate della Regione Siciliana (SITR):
  - riprese aeree 1977-79 e 1988-89;
  - Carta tecnica regionale (foglio 638070 "Mazzarino");
  - modello del terreno a 2 m (rilievo 2012-13).
- Risorse 3D: progetto Comune, Megascans, Megapack, Game Animation Sample (Epic). Musica e marchi protetti non vanno usati.
