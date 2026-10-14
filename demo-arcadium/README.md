# ARCADIUM 84 — pub bar d'arcade (marque fictive), synthwave / VHS

Pub verticale de 24,5 s (1080 × 1920), esthétique années 80 :
- soleil à rayures, grille néon en perspective, montagnes en fil de fer ;
- logo chromé, enseignes au néon qui grésillent ;
- borne d'arcade et jeu en pixel art (sprites originaux) ;
- couche VHS par-dessus : lignes de balayage, bavure des couleurs, tremblement de bande, bande de suivi, compteur « PLAY / REW / STOP ».

ARCADIUM 84, ses chiffres et ses horaires sont **inventés**. Tout est généré par code.

## Scènes et transitions

| Temps | Scène | Transition |
|---|---|---|
| 0–1,3 s | Neige télé, puis allumage du tube cathodique | — |
| 1,3–6,4 s | Paysage synthwave, le logo chromé arrive du fond, « 84 » et « BAR ARCADE » au néon | Rembobinage VHS |
| 6,9–10,4 s | Borne d'arcade avec le jeu en marche, néon « INSERT COIN », pièce qui tombe | Changement de chaîne (neige) |
| 10,8–14,4 s | Jeu de tir plein écran, score qui monte, « 60 BORNES · JEUX ILLIMITÉS » | Zoom à travers les pixels |
| 14,9–18,4 s | Néons dessinés : cocktail et joystick, « HAPPY HOUR 18H — 20H » | Glitch |
| 18,8–21,2 s | Retour au paysage : « CE VENDREDI · Soirée 80's » | Extinction du tube, puis rallumage |
| 22,4–24,5 s | Logo, BAR ARCADE, LYON, @arcadium84, « INSERT COIN TO CONTINUE » qui clignote | — |

## Son

Synthwave à 118 BPM en la mineur : arpèges en dents de scie, basse, nappes, caisse claire à réverbération coupée, lead avec glissando.

Bruitages : neige télé, allumage et extinction du tube, rembobinage de bande, pièce 8-bit, pièce qui tombe, tirs laser et explosions 8-bit, néons qui grésillent, clic de changement de chaîne, glitch, impacts.

## Régénérer

```bash
pip install numpy pillow scipy
npm pack @fontsource/jost@5 @fontsource/cormorant-garamond@5
for f in fontsource-*.tgz; do tar xzf "$f" && mv package "${f%.tgz}"; done
python3 arcadium.py . arcadium84-synthwave-24s.mp4
```
