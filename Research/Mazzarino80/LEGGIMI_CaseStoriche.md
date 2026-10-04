# Campione di case storiche — Mazzarino anni Ottanta

## Aprire e modificare

Mappa di studio: `/Game/Levels/Mazzarino80_CaseStoriche_Campione`.
Nel Content Browser: **Content → Levels → Mazzarino80_CaseStoriche_Campione**.
Nell'Outliner: **Mazzarino80 → Campione_case_storiche**. Le 18 case sono divise per famiglia. La generazione precedente è stata rimossa dalla mappa di studio.

È una copia autonoma della Panoramica salvata il 28 settembre. Le impronte XY, le spline stradali e le strutture personali sono conservate. La forma delle nuove abitazioni è una proposta architettonica, non una ricostruzione documentata dei singoli edifici nel 1980. La mappa principale e MazzarethMap conservano i loro file originali.

## Sei famiglie

| Famiglia | Composizione |
|---|---|
| Casa bassa popolare | Un piano, poche aperture, copertura modesta a coppi |
| Casa stretta | Tre piani, aperture verticali, balconi occasionali, terrazza |
| Casa d'angolo | Due fronti esposti, corpo principale e ala più bassa |
| Casa con cortile | Ali di altezze differenti intorno a un cortile aperto sul fronte |
| Casa ampliata | Corpo originario, ala bassa e sopraelevazione arretrata |
| Piccolo palazzetto | Due piani, prospetto più regolare, portale e pochi balconi |

I lotti concavi possono produrre più ali separate della stessa casa. I lotti ampi possono contenere più corpi addossati. Le divisioni sono interne al perimetro importato. Il carattere arabo-siciliano deriva da questo tessuto, senza aggiungere cupole o minareti.

## Parametri nel pannello Details

| Gruppo | Controlli |
|---|---|
| Grammatica | Famiglia, seed della singola casa, famiglia precedente, varietà volumi, irregolarità facciate, densità balconi, degrado |
| Dimensioni | Piani (0 = scelta della famiglia), altezza piano, spessore muri, rialzo ingresso, profondità balconi, rialzo copertura, parapetti |
| Dimensioni corte e strada | Larghezza/profondità corte in rapporto al lotto, arretramento sopraelevazione, alzata/pedata dei gradini, larghezza canaletta |
| Lotto | Spline del lotto, lato principale, elenco dei lati ciechi condivisi, identificativo |
| Appoggio | Aggiornamento automatico, attore strada dell'ingresso, attore terreno |
| Visibilità | Aperture, coperture, balconi, persiane, cornici, usura, dettagli quotidiani, gradini, canalette, numeri civici |
| Materiali | Intonaco, pietra, coppi, terrazza, ferro, legno, vetri, umidità, rappezzi, pietra esposta, tessuto, grigio |
| Moduli | Mesh del portone e del vaso, sostituibili con risorse del progetto |

**Rigenera solo questa casa** ricostruisce esclusivamente l'attore selezionato. Conservando seed e parametri, la geometria si ripete identica. I prospetti non vengono copiati da un'unica facciata: la famiglia cambia piani, volumi, aperture, balconi e coperture.

La scelta **Automatica ponderata** usa probabilità di base: popolare 32, stretta 24, angolo 12, corte 10 solo su lotti sufficientemente ampi, ampliata 16, palazzetto 6. La famiglia precedente pesa il 15% per ridurre ripetizioni. Nel campione le famiglie sono assegnate esplicitamente per mostrare tutti i casi; prima di estendere il generatore all'intero paese va nuovamente verificata l'adiacenza degli edifici.

## Terreno e verticalità

La strada indicata determina la quota dell'ingresso; se il terreno al fronte è più alto, prevale il terreno per evitare ingressi interrati. Il terreno determina anche il bordo inferiore delle fondazioni. Solai, balconi e terrazze restano orizzontali. I muri seguono lo Z globale; inclinazione e rollio vengono azzerati. La forma XY si modifica attraverso i punti della spline del lotto, senza inclinare o scalare l'intero attore.

L'editor controlla i supporti ogni secondo, anche con Realtime disattivato. Spostare i punti della spline stradale oppure modificare il terreno dotato di collisione aggiorna l'appoggio. **Aggiorna appoggio (Z verticale)** permette un controllo immediato. Se cambi attore terreno, assegnalo nel campo Terreno di appoggio. Le superfici senza collisione non forniscono quote utilizzabili.

L'automatismo segue le quote disponibili, ma non può trasformare un dislivello arbitrariamente grande in una scala comoda: dopo interventi importanti controllare ingressi, muri di sostegno e spazio libero della strada. Le scale più lunghe corrono lungo il muro; gli accessi secondari con oltre 1,5 m di dislivello o senza spazio sufficiente per i gradini vengono esclusi. Non sono create scale che continuano oltre l'angolo dell'edificio. Le quote del DSM moderno non certificano il terreno del 1980. L'aggiornamento automatico è attivo nell'editor; durante il gioco viene usata la geometria salvata.

## Geometria e usura

Porte e finestre sono tagliate nelle pareti, con imbotti, soglie e archi campionati. Gli ingressi profondi sono chiusi da portoni: gli interni abitabili non sono ancora modellati. Le pareti condivise non ricevono porte o balconi. Balconi singoli e alla francese usano mensole e ringhiere instanziate. Le cornici sono sottili e, nelle case più degradate, hanno tratti mancanti.

L'umidità segue la linea del terreno; le colature partono dai davanzali. Rappezzi e pietra esposta evitano le aperture. Maschere nei materiali irregolarizzano le macchie superficiali. L'invecchiamento è differenziato, non una distruzione uniforme. I numeri civici sono segnaposto decorativi, non indirizzi storicamente verificati.

Portoni e vasi riutilizzano risorse già copiate da Comune. Cavi, pluviali, antenne e pochi panni sono geometria semplice. Per la qualità finale servono varianti di ferramenta locale, mensole scolpite per i pochi edifici curati, persiane e intonaci specifici di Mazzarino; il campione permette di sostituire materiali e moduli.

## Verifiche e confronto

Il campo **Controllo forme: grigio uniforme** applica lo stesso materiale alle parti della casa. Le camere di confronto sono nella cartella Verifica: confronto originale, panoramica e vicolo. Le immagini e i risultati dei controlli sono in `Saved/Mazzarino80/Preview/Historic` e `Saved/Mazzarino80/Historic`.

La percorribilità va verificata sul percorso campione; i rapporti distinguono controlli di geometria/collisione da prove con il personaggio. La mappa di studio contiene ora soltanto le 18 abitazioni della nuova grammatica, oltre alle strutture recuperate, al terreno e alle strade. Gli altri lotti attendono la successiva estensione del generatore.

Sette spline di appoggio del campione hanno ora pietra consumata o cemento riparato, con trama in coordinate mondo per evitare stiramenti. Le cinque spline originariamente larghe 1,8 m sono state portate a 3 m nella sola copia, come proposta di pavimentazione del vicolo, senza spostare i punti o le quote. La larghezza resta modificabile nel pannello Strada. I materiali espongono colore e dimensione della trama; si possono creare istanze per modificarli. Il Corso conserva la pavimentazione lavica precedente. I bordi del terreno ancora chiari restano superfici provvisorie da rifinire, non marciapiedi storicamente documentati.

Le immagini esportate sono render effettivi dell'editor. Il primo confronto prima/dopo resta archiviato con la stessa camera e la stessa illuminazione. Dopo la pulizia, la modalità prima richiede la copia di sicurezza; non ricrea gli edifici rimossi. Le viste grigie riguardano esclusivamente le 18 case nuove.

### Esito della prima versione del 28 settembre 2026

- Mappa aperta e salvata in Unreal 5.5.3: 18 case, sei famiglie con tre esempi ciascuna.
- 13.767 triangoli della superficie procedurale complessiva, oltre ai dettagli instanziati; nessun triangolo degenere rilevato. Non è una misura delle prestazioni dell'intero paese.
- Rigenerazione deterministica e cambio del seed di una sola casa verificati senza modificare le altre.
- Spostamento della strada di +80 cm: ingresso aggiornato di +80 cm e casa verticale. Spostamento del terreno di +60 cm: aggiornamento della posizione o delle fondazioni di tutte le 18 case. Confermato anche l'aggiornamento automatico con Realtime disattivato; quote di prova ripristinate.
- Impronte XY dei 18 lotti: differenza massima 0 cm rispetto ai perimetri precedenti. Trasformazioni delle strutture recuperate conservate.
- Controllo con capsula di raggio 34 cm e semialtezza 88 cm su sette strade: le due interferenze al centro di via Catania hanno un passaggio libero comune a 15–35 cm lateralmente alla spline. I contatti con pavimentazioni in pendenza richiedono ancora la verifica del movimento del personaggio. Non è stato completato un giro in modalità Play.
- Hash della Panoramica e di MazzarethMap invariati rispetto all'inizio del lavoro.

Confronto interattivo: `Saved/Mazzarino80/Preview/Historic/Confronto.html`. Rapporti: `validation.json`, `live_support.json`, `integrity.json`, `routes.json`, `step_passage.json` nella cartella `Saved/Mazzarino80/Historic`.

## Pulizia e prima rifinitura del campione

Su richiesta dell'utente sono stati eliminati dalla sola mappa di studio i 3.216 attori della generazione precedente. Restano le 18 case storiche. Copia di sicurezza completa della mappa precedente: `Saved/Mazzarino80/Backups/Before_sample_cleanup_2026-09-28/Mazzarino80_CaseStoriche_Campione.umap`. I perimetri sono anche archiviati in `Saved/Mazzarino80/Historic/previous_lots.json`. Il vecchio codice rimane necessario per aprire le mappe di archivio, ma non genera abitazioni nella scena di lavoro.

L'editor apre ora il campione all'avvio. La Panoramica precedente e MazzarethMap sono conservate.

Le persiane usano legno verniciato consumato al posto dell'intonaco provvisorio. Il rilievo dell'intonaco è attenuato; ogni casa ha un'istanza del materiale nella cartella `Historic/Materials/Case`, con tinta, contrasto, rilievo e rugosità regolabili separatamente. Questi ultimi valori dipendono anche dal livello di manutenzione, mantenendo il seed dell'edificio. La pietra delle soglie ha una tonalità minerale più calda. L'umidità sfuma verso l'alto e i rappezzi hanno bordi meno frammentati.

Il terreno del campione usa una superficie neutra, sostituendo i margini verdi provvisori. Questa finitura non definisce ancora marciapiedi storici o una sistemazione definitiva del suolo.

Le nuove viste sono in `Saved/Mazzarino80/Preview/Historic/Refined`; aprire `Confronto.html` per confrontare la prima finitura con quella aggiornata e consultare vicolo, panoramica e viste grigie. Sono render acquisiti nell'editor dopo la correzione del materiale dell'umidità, non immagini illustrative. Sono stati salvati anche i materiali dei portoni e dei vasi con il supporto per le istanze.

La rifinitura non cambia i perimetri, le quote stradali o le strutture recuperate. Restano da sviluppare ferramenta locale, persiane più articolate, mensole scolpite, canalette meno frammentate e una verifica completa del percorso in Play. Il livello di studio è stato salvato e lasciato aperto dalla camera del vicolo.

## Rifinitura dei dettagli — versione attuale, 28 settembre 2026

Questa sezione aggiorna i risultati della prima versione descritta sopra. La mappa contiene sempre le stesse **18 case**, senza ripristinare la vecchia generazione.

### Correzioni applicate

- Davanzali: sporgenza esterna **5,5 cm**, spessore **4,5 cm**; l'imbotte rimane profondo senza trasformare la soglia in una mensola enorme.
- Pareti: chiusura dei due lati, estremità, fondi dei volumi e raccordi. I lati condivisi rimangono chiusi e ciechi; non vengono più saltati i brevi tratti di parete. Corretto anche l'orientamento dei perimetri prima della triangolazione.
- Tetti: falde con colmi e altezze differenti, **28.259 coppi tridimensionali instanziati**, compresi elementi sul colmo. Il modulo di coppo è stato creato per questo progetto; non è una scansione. Il materiale distingue argilla scura, chiara, depositi minerali e porosità. Le superfici di copertura sotto i coppi restano chiuse.
- Balconi: tubi tondi, volute semplici, mensole sagomate e profili delle lastre. Su alcune case d'angolo e palazzetti sono presenti **9 istanze di un balcone completo recuperato da Comune**, con balaustra in pietra e ferro. Questa variante curata non viene applicata a tutte le case popolari.
- Impianti: **112 spline modificabili** per cavi e pluviali. I cavi riutilizzano `SM_wire_part_01` di Comune; i pluviali hanno sezione tonda, curve terminali e staffe. Le canalette hanno sezione a U, griglie e materiale opaco separato.
- Facciate: cinque case con muratura a vista, tredici con calce consumata individuale. Coordinate continue sulle pareti evitano di ricominciare la trama della pietra sotto ogni finestra.

### Nuovi parametri modificabili

| Controllo | Uso / valore del campione |
|---|---|
| Sporgenza / spessore davanzali | 0,055 / 0,045 m |
| Diametro pluviali / cavi | 0,07 / 0,012 m |
| Freccia dei cavi | 0,22 m per i percorsi appena generati |
| Mostra coppi tridimensionali | Visibilità separata dalle falde |
| Passo file / lunghezza coppi | 0,20 / 0,36 m |
| Irregolarità coppi | Variazione geometrica controllata; non simula crolli |
| Conserva spline impianti | Attivo: mantiene i punti modificati manualmente |
| Ripristina spline impianti | Ricrea soltanto i percorsi di cavi e pluviali |
| Usa balconi completi / larghezza modulo | Abilita la mesh sulle famiglie compatibili e ne calibra la scala |
| Mesh e materiali | Coppo, cavo, balcone completo e canaletta sono sostituibili |
| Materiale dei coppi | Argilla scura/chiara, depositi grigi, quantità depositi, porosità e rugosità |

Per modificare un cavo o un pluviale, selezionare la casa e il componente spline dell'impianto, poi spostare i suoi punti. La rigenerazione conserva queste modifiche. **Se cambi freccia dei cavi o seed e vuoi ridisegnare anche gli impianti già esistenti, usa Ripristina spline impianti**: conservare i punti manuali ha precedenza sul nuovo tracciato automatico. Non inclinare la casa per adeguarla al terreno: il sistema mantiene pitch e roll a zero e aggiorna appoggi e fondazioni.

### Verifica effettivamente completata

- Compilazione del modulo per editor, gioco Development e Shipping riuscita.
- 146.095 triangoli procedurali, oltre alle mesh instanziate: zero triangoli degeneri e nessun errore di geometria riportato. I coppi aggiungono circa 5,8 milioni di triangoli istanziati prima del culling: **non è una certificazione delle prestazioni dell'intero paese**.
- Rigenerazione deterministica, modifica isolata del seed, prova strada +80 cm e terreno +60 cm riuscite; case verticali e quote di prova ripristinate.
- Spostamento manuale di un punto di cavo conservato dopo rigenerazione. Prova ripristinata.
- Salvataggio e vera riapertura della mappa: conservati punti delle 112 spline, seed, 28.259 coppi, 9 balconi completi e davanzali; 18 case ancora verticali. Rapporto `persistence.json`.
- Perimetri dei lotti: differenza massima XY 0 cm. Panoramica e MazzarethMap: hash originali invariati.
- Controlli di passaggio con capsula sulle sette strade del campione. Le due interferenze lungo via Catania consentono un passaggio spostato lateralmente; **resta da completare una prova del movimento del personaggio in Play**.
- Render dell'editor dalla strada, dal vicolo, dall'alto e con materiale grigio uniforme. Le strutture personali esterne alle 18 case mantengono i loro materiali anche nelle viste grigie.

Durante l'esame di una texture l'esportatore TGA di Unreal 5.5 ha provocato un arresto per tipo non supportato. La mappa era già salvata, è stata riaperta e i render finali sono stati acquisiti dal progetto recuperato; quell'esportazione non viene più utilizzata.

### Confronto e qualità ancora da sviluppare

Aprire **`Saved/Mazzarino80/Preview/Historic/Confronto_dettagli.html`**: confronta i render `BeforeDetails` con `Details` nelle stesse camere. Comprende dettagli di tetto e balcone e viste grigie. I vecchi confronti restano archiviati separatamente.

Le risorse di Comune sono sufficienti per questa iterazione: non è stato acquistato o scaricato alcun pacchetto. Il Roof Kit e altri due moduli di balcone sono importati ma non ancora distribuiti sulle case. Per raggiungere la ricchezza delle immagini di riferimento servono ulteriori varianti di persiane, portoni siciliani, ringhiere in ferro e mensole locali, oltre a una passata dedicata su usura, raccordi a terra e bordi dei coppi. Le facciate di calce e alcune coperture rimangono più pulite e regolari del riferimento. Non sono ancora modellati interni abitabili.

Street View moderno guida proporzioni e dettagli, senza attestare l'aspetto storico degli edifici nel 1980; vedere `Riferimenti_dettagli.md`.
