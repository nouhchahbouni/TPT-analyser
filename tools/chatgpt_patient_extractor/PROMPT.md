# Prompt réutilisable — Extraction des conversations patients (Dr Rifay)

Copie-colle ce prompt (avec les nouveaux fichiers `conversations-XXX.json` en
pièce jointe) pour relancer le traitement sur un nouveau lot.

---

J'ai un export ChatGPT d'un cabinet d'ophtalmologie (Dr Rifay), au format
export standard (`mapping` avec `parent`/`current_node`, messages
`author.role` = `user`/`assistant`, contenu dans `content.parts`, avec des
messages `multimodal_text` contenant des `audio_transcription`).

Utilise le script `tools/chatgpt_patient_extractor/extract_patient_conversations.py`
déjà présent dans le repo (branche `claude/extract-patient-conversations-0onkjd`)
et applique-le sur les nouveaux fichiers. Voici les règles qu'il doit
respecter (à ajuster/étendre si les nouveaux lots révèlent des cas non
couverts) :

## 1. Objectif

Ne garder QUE les conversations où un vrai patient (ou abonné réseaux
sociaux) écrit, à la première personne, un message médical adressé au
médecin/cabinet (symptôme, éligibilité à une opération, question sur une
maladie/traitement) — et où l'IA répond comme si elle répondait au patient.
Le staff colle ces messages WhatsApp/réseaux dans ChatGPT pour obtenir une
réponse à renvoyer.

## 2. Exclure (majorité du contenu du cabinet)

- Dictées de documents internes : comptes rendus, rapports, bilans,
  consentements, certificats, ordonnances, lettres administratives.
- Recherche juridique/médicale du staff (droit marocain, interprétation
  d'examen, questions de connaissance médicale générale sans patient réel).
- Descriptions de patients à la 3e personne ("Mr X, âgé de 23 ans...").
- Courriers à des confrères ("cher confrère, je vous adresse ce patient").
- Candidatures/entretiens d'embauche (CV, stage, poste).
- Production de contenu : traduction, légende de post, logo, affiche,
  script vidéo, hashtags, captions Instagram/YouTube, FAQ.
- Notes internes d'organisation, plannings, mises à jour de tarifs internes,
  branding, rôles du personnel.
- Instructions génériques du staff pour répondre à "des gens/abonnés" sans
  message précis collé.
- Salutations isolées sans substance, conversations vides.
- **Rendez-vous** : prise/confirmation/annulation/report d'un rendez-vous
  (géré ailleurs).
- **Prix** : devis, tarif, combien/coût/estimation d'une opération ou d'un
  examen (géré ailleurs).
- **Demande de recommandation de confrère** : "connaissez-vous un
  spécialiste pour X ?" (géré ailleurs).
- **Demande de contact pur** : "donnez-moi votre numéro", sans aucune
  question médicale.

## 3. Garder

Message patient en français, arabe ou darija (y compris darija translittérée
en caractères latins, ex. "3andi", "chhal", "wach", "bghit") posant une vraie
question médicale : symptôme, éligibilité à une chirurgie, traitement
possible, suites post-opératoires, plainte sur la prise en charge/qualité de
service. Un proche qui écrit pour un patient (parent, frère/sœur) compte
aussi comme un vrai message patient.

## 4. Classifieur en 2 passes

1. Règles regex dures (voir liste des catégories d'exclusion ci-dessus) sur
   le premier message utilisateur.
2. Score fin sur ce qui reste : voix à la 1ère personne (FR/AR/darija/
   arabizi) + adresse au médecin/cabinet + intention patient (symptôme,
   traitement, opération) + vocabulaire ophtalmo, avec pénalité si le
   message est très long/structuré (signe de dictée clinique).

## 5. Extraction de l'échange propre (par conversation retenue)

- Le "message du patient" = le premier tour `user`, pas forcément le tout
  premier tour du fil (certains fils commencent par un message d'accueil de
  l'IA).
- Retirer du message du patient les instructions internes collées dans le
  même tour ("Repondre...", "Repondre a la maniere dr rifay"...), y compris
  en tête de message. Si le message se termine par une formule de politesse
  + signature ("Cordialement", "Best regards"), couper net après : tout ce
  qui suit dans le même tour est une note interne du staff.
- La "réponse" = la réponse IA qui répond réellement à CETTE question,
  obtenue en suivant les tours suivants MAIS en ne continuant que si le tour
  utilisateur suivant est une instruction de mise en forme explicite
  (traduire, raccourcir, corriger, changer de ton...). Toute autre demande
  (même courte), y compris une nouvelle question sur un tout autre sujet
  plus loin dans un fil réutilisé par le staff, arrête l'échange : on garde
  la dernière réponse pertinente, pas celle d'un sujet différent posé plus
  tard.
- Si deux réponses IA se suivent sans instruction du staff entre les deux,
  c'est qu'un tour utilisateur invisible (image, pièce jointe) a changé de
  sujet : s'arrêter à la réponse précédente.
- Nettoyer la réponse IA : retirer le préambule ("Voici une proposition..."),
  les questions de suivi adressées au staff ("Voulez-vous que je...?",
  "تحب نـ...؟"), extraire le contenu entre "---" ou entre guillemets quand
  la réponse suggérée y est enfermée, retirer les résidus de citations web
  invisibles (`citeturnXsearchY` et caractères Unicode de zone d'usage
  privé qui les entourent).
- Retirer de la réponse toute proposition de rendez-vous et tout bloc de
  contact (téléphone/WhatsApp/adresse/secrétariat), pour ne garder que la
  réponse médicale directe à la question posée — sauf si le contenu du
  numéro/rendez-vous répond lui-même directement à ce qui a été
  explicitement demandé par le patient (rare, ces cas sont de toute façon
  exclus en amont comme "prix"/"rendez-vous"/"contact pur").
- Si un numéro de téléphone du cabinet apparaît malgré tout dans une réponse
  gardée, le remplacer par les numéros officiels : fixe 0537686854, WhatsApp
  0667665449 / 0766024606 / 0623682514. Sinon ne rien faire.

## 6. Anonymisation

Remplacer les noms de patients précédés d'un titre (Mr/Mme/Dr...) par
`[NOM]`, les adresses par `[ADRESSE]`. Le reste du texte reste intact.

## 7. Sorties

- `.txt` : chaque conversation retenue sous la forme
  `CONVERSATION i/N` / `Titre` / `ID` / `Fichier` puis
  `[DEMANDE DU PATIENT]` / `[REPONSE DE L'IA]`, séparées par une ligne de
  `=`.
- `.csv` : id, titre, fichier source, aperçu du premier message — pour
  vérification manuelle des faux positifs/négatifs.
- Statistiques : total, retenues, répartition des raisons d'exclusion.

## 8. Process

1. Copier les nouveaux fichiers dans un dossier `data/`.
2. Lancer :
   ```
   python tools/chatgpt_patient_extractor/extract_patient_conversations.py \
     --input-dir ./data --output-txt patient_conversations.txt \
     --output-csv patient_conversations_review.csv
   ```
3. Relire les nouvelles conversations retenues en entier (pas seulement
   l'aperçu du CSV) pour vérifier que la réponse correspond bien à la
   question posée — les fils très longs (staff qui réutilise le même fil
   ChatGPT pour plusieurs sujets/patients dans la journée) sont les plus à
   risque de désaccord question/réponse.
4. Si des faux positifs/négatifs apparaissent, ajuster les règles regex du
   script (catégories d'exclusion ou score de la passe 2) plutôt que de
   corriger le fichier de sortie à la main, pour que la correction profite
   aussi aux prochains lots.
5. Ne jamais committer les fichiers d'export bruts ni les fichiers de
   sortie (`.txt`/`.csv`) dans git — ils contiennent des données de santé
   de vrais patients (déjà dans `.gitignore`). Seul le script est versionné.
