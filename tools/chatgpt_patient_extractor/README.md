# ChatGPT Patient Conversation Extractor

Script pour extraire, depuis un export ChatGPT (`conversations*.json`), les
conversations où un vrai patient (ou abonné réseaux sociaux) écrit au
cabinet, en excluant le travail interne du staff (dictées de comptes
rendus, courriers confrères, recherches juridiques, traductions,
production de contenu, etc.).

## Usage

```bash
# 1. Déposer tous les lots d'export dans un dossier, p.ex. ./data
#    (conversations-000.json, conversations-001.json, ...)

# 2. Lancer l'extraction
python extract_patient_conversations.py \
    --input-dir ./data \
    --output-txt patient_conversations.txt \
    --output-csv patient_conversations_review.csv
```

Le script affiche des statistiques (total, retenues, répartition des
raisons d'exclusion) à la fin de l'exécution.

## Relançable / nouveaux lots

Le script ne garde aucun état entre deux exécutions : il rescanne
`--input-dir` (récursivement, tout fichier dont le nom contient
`conversations`) à chaque lancement et régénère les deux fichiers de
sortie à partir de l'ensemble des lots présents. Pour ajouter un nouveau
lot, il suffit de le déposer dans le dossier d'entrée et de relancer la
commande. Les conversations dupliquées (même `conversation_id` dans
plusieurs lots) sont automatiquement dédupliquées.

## Fonctionnement du classifieur (2 passes)

1. **Passe 1 (règles sûres)** : exclut par regex tout ce qui ressemble
   clairement à du travail interne (dictée de rapport/consentement/
   certificat, description de patient à la 3e personne, courrier à un
   confrère, traduction/légende/logo/affiche, recherche juridique,
   admin interne, dictée de données d'examen clinique).
2. **Passe 2 (score fin)** : pour ce qui reste, calcule un score sur le
   premier message de l'utilisateur à partir de : voix à la 1ère
   personne (FR/AR/darija), adresse explicite au médecin/cabinet,
   intention patient (RDV, prix, symptôme, contact), et vocabulaire
   ophtalmologique. Le message est retenu si le score dépasse un seuil.

Comme toute classification par règles sur du texte multilingue
(français/arabe/darija), le résultat n'est pas parfait : c'est le rôle du
CSV de contrôle (`patient_conversations_review.csv`) de permettre une
vérification manuelle rapide (id, titre, aperçu du 1er message) pour
repérer les faux positifs/négatifs. Les regex peuvent être affinées dans
`extract_patient_conversations.py` (sections "Passe 1" et "Passe 2") au
fur et à mesure des lots traités.

## Anonymisation

Une anonymisation best-effort par regex remplace :
- les noms précédés d'un titre (`Mr`, `Mme`, `Dr`, ...) par `[NOM]` ;
- les adresses (rue, avenue, quartier, résidence, ...) par `[ADRESSE]`.

Le reste du texte n'est pas modifié. Cette anonymisation est partielle
(regex, pas de NER) : une relecture humaine du fichier `.txt` avant toute
diffusion externe reste nécessaire.

## Confidentialité

Les fichiers d'export et les fichiers générés (`.txt`, `.csv`) contiennent
des données de santé de vrais patients. Ils sont volontairement exclus du
dépôt git (voir `.gitignore` : `tools/chatgpt_patient_extractor/data/`,
`*.txt`, `*.csv` dans ce dossier) : ne jamais les commiter.
