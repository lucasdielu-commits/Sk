# ORVA — démo motion design (marque fictive)

Pub verticale de 29,5 s (1080 × 1920, 30 i/s) dans le style « app promo ». ORVA, ses chiffres et ses personnages sont **inventés**. Tout est dessiné par code, sans aucune image.

## Fichiers

- `orva-motion-design-30s.mp4` : version 1
- `orva-motion-design-v2-30s.mp4` : version 2, améliorée
- `orva2.py` : rendu de la v2
- `orva_audio.py` : bande-son de la v2
- `orva.py` + `music_motion.py` : v1

## Ce que la v2 change

| | v1 | v2 |
|---|---|---|
| Contours | Formes dessinées en escalier (crénelage) | Toutes les formes sur-échantillonnées 3x (boutons, icônes, anneaux, courbe, bâtiments, carte) |
| Typo | Faux italiques, halos rouges partout | Titres droits et serrés, halos discrets, lueur réservée au logo et au point |
| Mouvement | Flou appliqué à quelques éléments | Vrai flou de mouvement façon caméra : 3 sous-images par image, 9 sur les passages rapides |
| Image | Plate | Bloom des hautes lumières, aberration chromatique sur les bords, très légère caméra portée, grain fin |
| Transitions | Décalage de l'image entière | Balayages où les deux plans bougent ensemble, zoom traversant, flash avec fuite de lumière, glitch par tranches, passage par le noir, secousses amorties |
| Son | Musique + quelques bruitages | Musique produite (sidechain, filtres, coupure avant « Transaction », reverb) et environ 70 bruitages calés à l'image : cœur, flash, frappe clavier, taps, pops, roulement de compteur, message reçu ou envoyé, validation, glitch, carte qui tourne, montées, notifications, grondement et chocs des bâtiments, bip du terminal, scintillement du logo, impacts. Volume normalisé à -13 LUFS |

## Régénérer

```bash
pip install numpy pillow scipy
npm pack @fontsource/jost@5 && tar xzf fontsource-jost-*.tgz && mv package fontsource-jost-5.3.0
python3 orva2.py . orva-motion-design-v2-30s.mp4
```
