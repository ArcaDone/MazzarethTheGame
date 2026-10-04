# Case procedurali V2 — guida d'uso

Il generatore V2 sostituisce il vecchio "PCG" delle 18 case (che in realtà era un bake Python con coordinate fisse). Vive nel plugin `Plugins/MazzarinoHouses` ed è scritto in C++.

## Come si usa in Unreal

1. **Piazzare una casa:** Place Actors → cerca **"Casa Mazzarino (procedurale)"** (`AM80House`) e trascinala nella mappa.
2. **Perimetro:** è una spline chiusa con punti lineari. Seleziona i punti e spostali come una qualsiasi spline (Alt+trascina per aggiungerne). La casa si rigenera mentre trascini.
3. **Parametri** (pannello Dettagli, categoria *Casa*):
   - *Stile*: uno dei quattro asset in `Content/Mazzarino80/Houses/Styles` (01 popolare in pietra, 02 palazzo urbano, 03 intonacata anni '50-'70, 04 casa povera).
   - *Numero piani*, *altezza piano terra*, *altezza piani superiori*, *variante (seed)*.
   - *Finitura muri* e *Degrado*.
   - *Tetto*: a capanna, una falda o terrazza; pendenza; colmo parallelo alla facciata.
   - *Lati*: la facciata principale e i muri in comune vengono rilevati da soli; puoi forzarli con *Lato facciata principale* e *Tipo di ogni lato*.
   - *Schiera*: i lotti OSM lunghi vengono divisi in case a schiera di 4,8-9 m, ognuna con piani, finitura, colore, degrado e tetto propri. Puoi disattivarlo o cambiare le larghezze.
   - *Terreno*: la casa segue il terreno (tracce verso il basso, ignorando le altre case). Il piano terra di ogni casa della schiera parte dalla quota della strada davanti al suo ingresso; verso valle compare un piano seminterrato con porte di cantina e finestrelle.
4. **Rigenera / Rigenera con i vicini:** pulsanti nel pannello. Il secondo serve quando sposti una casa e i muri in comune dei vicini devono aggiornarsi.
5. **Stato generazione** mostra case, triangoli, aperture, balconi, quote e tempo di calcolo.

### Gli stili
Ogni stile (`UM80HouseStyle`) contiene i materiali e le regole di facciata: larghezza delle campate, misure di finestre e porte, probabilità di balconi, persiane aperte o chiuse, tapparelle, portali ad arco, garage, cantonali o paraste, marcapiano, zoccolo, cornicione, pendenza e sporto del tetto, comignoli. Modificando lo stile cambiano tutte le case che lo usano, alla prossima rigenerazione.

### Il master material
`Content/Mazzarino80/Houses/Materials/M_M80_HouseMaster`, con un'istanza per ogni finitura (conci, pietrame, intonaco, intonaco rovinato), cornici in arenaria, coppi, terrazza, legno verniciato, ferro e vetro.
- Texture a scala reale (UV in metri).
- *Palette* di 3 colori per stile: ogni casa della schiera pesca il suo colore dal canale UV1.
- *Degrado*: l'intonaco cade dove rumore e rilievo coincidono e scopre pietra o mattoni sotto.
- *Umidità di risalita*: scurisce la base dei muri seguendo il terreno (colore di vertice R = altezza da terra).
- Variazione per elemento: ogni coppo, persiana o concio ha una tonalità leggermente diversa.
- Texture Megascans copiate in `Houses/Textures`, ridotte a 2K e con sorgente JPEG: 38 MB in tutto.

## Script (cartella `Scripts`)

Si lanciano con l'editor chiuso:
```
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/<script>.py
```

| Script | Cosa fa |
|---|---|
| `m80_houses_v2_setup.py` | Crea o aggiorna gli stili e la mappa di prova `Houses/Maps/L_M80_Houses18_V2` con le 18 case; fa le catture in `Saved/Mazzarino80/HousesV2/Views`. |
| `m80_house_materials.py` | Copia le texture, crea master e istanze, le assegna agli stili (`M80_REBUILD_MASTER=1` ricrea il grafo). |
| `m80_houses_district.py` | Crea `L_M80_District_V2` (copia della Panoramica) con tutte le case OSM entro un raggio (`M80_DISTRICT_RADIUS_M`, predefinito 160 m), salvando Matrice, Comune e le altre strutture fatte a mano. |
| `m80_houses_bake.py` | "Cuoce" le case di una mappa in Static Mesh Nanite (`M80_BAKE_MAP`). |
| `m80_profile_scene.py` | Misura frame, GPU e draw call su viste fisse (`M80_PROFILE_MAP`, `M80_PROFILE_HOUSE_VIEWS=1`). |

## Cottura (bake) e prestazioni

Mentre modifichi, la casa è una *mesh dinamica*: si rigenera in 10-200 ms, ma non è Nanite e Lumen la illumina male (le ombre restano nere). Per la versione finale si usa **Cuoci**: la casa diventa una Static Mesh Nanite con distance field (`Houses/Baked/<mappa>`), la mesh dinamica viene svuotata e la mappa resta leggera. Qualsiasi modifica alla casa la riporta in anteprima finché non la cuoci di nuovo.

Le mesh cotte e le mappe di quartiere sono **dati derivati**: sono escluse da Git (`.gitignore`) e si rigenerano con gli script.

## Cose da sapere
- `Mazzarino80_CaseStoriche_Campione` (il vecchio campione) non viene più modificato dagli script; la mappa di lavoro è `L_M80_Houses18_V2`.
- Se una casa sembra avere un angolo sbagliato basta spostare i punti della spline: non serve rilanciare nulla.
