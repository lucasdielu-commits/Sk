# LUNÉO — pub train de nuit (marque fictive), papier découpé

Pub verticale de 25,5 s (1080 × 1920), style papier découpé façon stop-motion : couches de papier texturé aux bords irréguliers, ombres portées, animation à 12 images par seconde avec frémissement des découpes, profondeur par couches. LUNÉO, ses destinations et ses prix sont **inventés**. Tout est généré par code.

## Scènes et transitions

| Temps | Scène | Transition |
|---|---|---|
| 0–3 s | Un billet glisse sur le bureau, tampon « CE SOIR », « Et si tu partais ? » en lettres découpées | Papier déchiré en deux |
| 3,6–7 s | Paris la nuit : immeubles éclairés, tour, lune qui se lève, le train entre en gare | Page tournée |
| 7,6–11 s | Les Alpes enneigées, le train traverse le viaduc, « Tu t'endors à Paris… » | Pliage en accordéon |
| 11,7–15 s | Lever de soleil sur la mer, mouettes, vagues, « …tu te réveilles face à la mer. » | Bandes qui glissent |
| 15,5–18,8 s | Carte : itinéraires en pointillés depuis Paris, épingles, « 12 destinations », pastille « dès 39 € » | Découpe ronde |
| 19,4–22 s | La cabine : paysage qui défile par la fenêtre, lit, tasse fumante, « Draps frais. Café au réveil. » | Papier déchiré |
| 22,6–25,5 s | Logo « Lunéo » en lettres découpées, « Le train de nuit, réinventé. », « RÉSERVER MA NUIT », @luneo.train | — |

## Son

Folk acoustique en sol majeur à 100 BPM : guitare en cordes pincées (Karplus-Strong), basse, balais, claquements de mains, glockenspiel.

Bruitages : froissement de papier, déchirure, page, tampon, roulement du train, sifflet, mouettes, vagues, cuillère dans la tasse, rebonds de papier.

## Régénérer

```bash
pip install numpy pillow scipy
npm pack @fontsource/jost@5 && tar xzf fontsource-jost-*.tgz && mv package fontsource-jost-5.3.0
python3 luneo.py . luneo-train-de-nuit-25s.mp4
```
