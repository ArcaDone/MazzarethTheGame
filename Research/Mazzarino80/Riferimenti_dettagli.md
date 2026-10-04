# Rifinitura delle 18 case — riferimenti e scelte

## Riferimento stradale

Google Street View, 169 Corso Vittorio Emanuele II, Mazzarino: immagine di novembre 2024 consultata il 28 settembre 2026.

https://www.google.com/maps/@37.3050432,14.2144416,3a,75y,251.66h,90t/data=!3m7!1e1!3m5!1sOkcWIH48ZU65XpoHj35M9g!2e0!7i16384!8i8192

Osservazioni visive: balconi con mensole e parapetti differenti, muratura e intonaco con manutenzione disomogenea, aperture con proporzioni diverse, piani prevalentemente bassi. Il riferimento moderno serve per leggere architettura e proporzioni; automobili, impianti recenti, arredo urbano e altri dettagli contemporanei non sono prova del loro aspetto nel 1980.

## Risorse già possedute nel progetto Comune

- Megascans Modular Building Balcony: balcone completo da valutare sulle case curate, senza estenderlo a tutte le abitazioni popolari.
- Megapack MiddleEast `BP_Wires`: verificato nello staging, usa `SM_wire_part_01` lungo spline con asse X. Il nuovo generatore riutilizza quella mesh per cavi con punti modificabili.
- Megascans Modular Building Roof Kit: cinque pezzi esaminati e importati nella libreria; le dimensioni sono circa 1,5–6 m e comprendono una copertura completa. Non sono singoli coppi, perciò non vanno deformati indiscriminatamente sui lotti irregolari.
- `Migrated/Balcony` e `Balcony2`: disponibili nella libreria isolata per ulteriori varianti; richiedono una calibrazione dell'ancoraggio prima di distribuirli.

La nuova libreria è in `Content/Mazzarino80/Library/ComuneDetail`; il progetto Comune originale è stato solo letto. Il coppo riutilizzabile è stato modellato appositamente per adattare le falde ai lotti senza deformare interi edifici.
