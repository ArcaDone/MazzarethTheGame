# Mazzarino: prima fase edifici

## Mappe

- **Mazzarino80_Panoramica**: terreno e strade nel sistema corretto dopo il ribaltamento globale dell'asse Y, 3.216 perimetri edilizi separati, primo campione vicino al Corso e prima posa di Comune, Matrice e San Domenico.
- **Mazzarino80_Catalogo**: le dieci strutture personali affiancate, con i loro componenti e materiali originali. Le altre sette strutture sono qui disponibili per il successivo allineamento nella città.
- **MazzarethMap**: conservata. SHA256 atteso `64B9F8A58710730F280A05473B72BB06E30665ADA67B067447E44D67D19A6541`.

## Modificare un edificio

Nell'Outliner aprire `Mazzarino80/Edifici`. Ogni `M80_Edificio_<numero OSM>` è un edificio autonomo.

1. Selezionare l'edificio e il componente **Perimetro**. Spostare i punti della spline per correggere la sagoma. Il contorno è chiuso, con lati rettilinei.
2. Nei dettagli dell'attore cambiare **Numero piani**, **Altezza piano (metri)**, **Materiale facciata**, **Materiale tetto**, **Rialzo tetto (metri)** e **Direzione colmo (gradi)**. Rialzo zero produce una copertura piana.
3. Per le facciate del campione sono disponibili **Aggiungi porte e finestre**, **Lato ingresso**, mesh di porte e finestre, dimensioni e passo delle finestre. Il lato ingresso indica il segmento della spline a partire da zero.
4. Usare **Rigenera edificio** dopo una modifica se la vista non si aggiorna. Per spostare la quota dell'intero edificio, spostare l'attore sull'asse Z: il pavimento resta piano.

Pareti e tetto hanno collisione. I moduli di porte e finestre sono elementi esterni: gli interni e le aperture percorribili saranno una fase successiva.

## Organizzazione

- `Isolato_campione`: 14 edifici con materiali, coperture, porte e finestre di prova.
- `Centro_Corso` e `Altri_quartieri`: volumi provvisori suddivisi per settori.
- `Strutture_recuperate`: le prime tre strutture personali posate.
- `Perimetri_sostituiti`: perimetri conservati ma nascosti dove sono stati inseriti i modelli personali.
- `Riferimenti_disattivati`: vecchia mesh unica degli edifici, conservata con visibilità e collisione disattivate.

Le risorse recuperate da Comune sono sotto `/Game/Mazzarino80/Library/Comune`, mantenendo le sottocartelle dei pacchetti per rintracciarne la provenienza. Il progetto Comune resta la sorgente di riferimento.

## Limiti e lavoro successivo

I perimetri sono quelli dei dati OSM attuali. Piani, altezze, coperture e aspetto del campione sono indicativi, non una ricostruzione storicamente verificata del 1980. I modelli personali sono in prima posa: quote d'ingresso, piazze, marciapiedi, orientamento dei fronti e possibili sovrapposizioni vanno rifiniti sul posto.

Alcuni perimetri OSM rappresentano blocchi edilizi ampi. Ora il prospetto viene scandito con più ingressi, cornici e dislivelli del tetto, mantenendo l'unico contorno originale. Corti e vuoti interni non sono ricavati automaticamente dai soli contorni esterni disponibili. Gli interni restano una fase successiva.

Proseguire con l'allineamento di Comune–Matrice–San Domenico e dell'isolato campione, poi collocare le altre strutture personali e rifinire i quartieri in sequenza. Vegetazione, cartelli, arredi e veicoli richiedono una scelta coerente con l'epoca.

## Verifiche registrate

`Saved/Mazzarino80/buildings_phase_result.json`: creazione e prima posa.

`Saved/Mazzarino80/buildings_validation.json`: riapertura, coincidenza dei perimetri, presenza delle strade, collisioni del campione e modifica del numero di piani.

Backup precedente alla fase: `Saved/Mazzarino80/Backups/Before_buildings_2026-09-28`.

## Aggiornamento prospetti e skyline — 28 settembre 2026

Sono stati articolati **213 edifici** lungo il Corso e aggiornate le coperture di **3.207 volumi visibili**. I nove perimetri sostituiti dai modelli personali restano nascosti. I punti dei perimetri, le strade e le ultime trasformazioni delle tre strutture recuperate sono stati conservati, insieme agli alberi aggiunti dall'utente.

I nuovi materiali usano direttamente le texture di intonaco, pietra e coppi recuperate da Comune. Sostituiscono sui volumi procedurali le precedenti istanze che apparivano grigie a scacchi. Sono presenti davanzali e cornici in rilievo, fasce marcapiano, zoccoli, persiane, balconi con solette e ringhiere a montanti, coperture a falde, parapetti e piccoli vani sulle terrazze quando il perimetro lo consente.

### Controlli aggiunti nei dettagli dell'edificio

- **Variante composizione**: varia la sequenza di altezze, finestre e balconi; resta stabile fra le rigenerazioni.
- **Larghezza prospetto (metri)**: scandisce gli ingressi e le porzioni del fronte nei perimetri lunghi.
- **Variazione altezze (metri)**: genera dislivelli reali delle coperture; zero mantiene un coronamento uniforme.
- **Tipo balconi**: 0 nessuno, 1 singoli, 2 continui; **Profondita balconi** modifica lo sbalzo.
- **Persiane** e **Decora anche i lati**: consentono di adattare i lati visibili degli edifici d'angolo. Disattivare la decorazione dei lati quando ci sono muri condivisi.
- **Terrazza con vano arretrato**: funziona sulle coperture piane; il piccolo volume viene creato solo se la sua sagoma entra nel perimetro.
- **Materiale cornici**, **Materiale ringhiere**, **Materiale persiane**: modificabili separatamente dalla facciata.

Le ringhiere e le persiane sono dettagli visivi; pareti e coperture hanno collisione. I balconi non sono ancora superfici calpestabili con interni accessibili. La composizione è una prima base architettonica, da rifinire edificio per edificio: non riproduce ogni singola casa reale.

**M80_Camera_Confronto_90**, nella cartella `Mazzarino80/Verifiche`, conserva posizione e direzione della vista fornita dall'utente con FOV orizzontale 90°. Il valore 53,43° trovato nelle impostazioni riguarda l'editor degli asset, non prova un FOV errato nella vista della mappa. La scala della Matrice non è stata ulteriormente modificata sulla base delle sole immagini.

**M80_Camera_Skyline** consente di osservare dall'alto gli isolati vicino alla Matrice e verificare falde, terrazze e coronamenti. Le due camere sono riferimenti di lavoro: non sostituiscono la camera del personaggio.

Controllo finale: 130.971 triangoli delle superfici visibili esaminati, nessun triangolo con vertici coincidenti; quattro campioni di collisione delle coperture superati; modifica di un punto del perimetro e ripristino verificati. Le texture virtuali di intonaco e coppi sono state corrette e controllate nella vista renderizzata. Balconi e coperture sono stati ispezionati sia dalla strada sia dall'alto.

Riferimenti: Street View nello screenshot dell'utente, 222 Corso Vittorio Emanuele II, giugno 2025; [scheda ufficiale della Matrice](https://chieseitaliane.chiesacattolica.it/chieseitaliane/AccessoEsterno.do?code=6605&mode=guest&type=auto), che descrive coperture a falde con coppi siciliani e facciata visibile di scorcio; [guida SideFX alla composizione degli edifici](https://www.sidefx.com/community/making-the-procedural-buildings-of-the-finals-using-houdini/). Il riferimento del 2025 aiuta la composizione attuale: non certifica balconi, colori o altezze nel 1980.

Verifiche: `Saved/Mazzarino80/facade_variety_report.json` e `facade_variety_validation.json`. Backup prima dell'aggiornamento: `Saved/Mazzarino80/Backups/Before_facade_variety_2026-09-28`.
