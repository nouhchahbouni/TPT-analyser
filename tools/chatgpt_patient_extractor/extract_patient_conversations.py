#!/usr/bin/env python3
"""
Extrait, depuis un export ChatGPT (fichiers `conversations*.json`), les
conversations où un vrai patient (ou abonné réseaux sociaux) écrit au
cabinet d'ophtalmologie, et exclut le travail interne du staff (dictées
de comptes rendus, courriers confrères, recherches juridiques, traductions,
production de contenu, etc.).

Usage:
    python extract_patient_conversations.py --input-dir ./data \
        --output-txt patient_conversations.txt \
        --output-csv patient_conversations_review.csv

Relançable: le script ne garde aucun état entre les exécutions, il
rescanne simplement --input-dir (récursivement) à chaque lancement. Il
suffit donc de déposer de nouveaux lots `conversations-XXX.json` dans ce
dossier et de relancer la commande pour regénérer les fichiers de sortie
à partir de l'ensemble des lots disponibles.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


# ---------------------------------------------------------------------------
# 1. Lecture des exports et linéarisation du mapping
# ---------------------------------------------------------------------------

def find_conversation_files(input_dir: Path) -> list[Path]:
    """Trouve tous les fichiers d'export ChatGPT (conversations*.json)."""
    files = sorted(
        p for p in input_dir.rglob("*.json")
        if "conversations" in p.name.lower()
    )
    return files


def load_conversations(path: Path) -> list[dict]:
    """Charge un fichier d'export : soit une liste de conversations, soit
    une conversation unique, soit un objet {"conversations": [...]}."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "conversations" in data and isinstance(data["conversations"], list):
            return data["conversations"]
        if "mapping" in data:
            return [data]
    raise ValueError(f"Format d'export non reconnu dans {path}")


def _extract_text_from_content(content: dict | None) -> str:
    """Extrait le texte visible d'un objet `content` de message, en gérant
    les types `text` et `multimodal_text` (avec audio_transcription)."""
    if not content:
        return ""
    content_type = content.get("content_type")
    parts = content.get("parts") or []

    if content_type == "text":
        return "\n".join(p for p in parts if isinstance(p, str)).strip()

    if content_type == "multimodal_text":
        chunks = []
        for part in parts:
            if isinstance(part, str):
                chunks.append(part)
            elif isinstance(part, dict) and part.get("content_type") == "audio_transcription":
                text = part.get("text") or ""
                if text:
                    chunks.append(text)
            # les autres types de part (audio_asset_pointer, image_asset_pointer,
            # real_time_user_audio_video_asset_pointer, ...) ne portent pas de
            # texte exploitable et sont ignorés.
        return "\n".join(chunks).strip()

    # Types non textuels (code, execution_output, tether_*, reasoning_recap,
    # thoughts, ...) : on ne les affiche pas dans la conversation reconstruite.
    return ""


def linearize_conversation(conv: dict) -> list[tuple[str, str]]:
    """Reconstruit le fil de discussion en suivant `current_node` puis les
    `parent` jusqu'à la racine, et renvoie la liste ordonnée des tours
    (role, texte) pour role in {"user", "assistant"}."""
    mapping: dict = conv.get("mapping") or {}
    current_id = conv.get("current_node")

    chain = []
    seen_ids = set()
    while current_id and current_id in mapping and current_id not in seen_ids:
        seen_ids.add(current_id)
        node = mapping[current_id]
        chain.append(node)
        current_id = node.get("parent")
    chain.reverse()

    turns: list[tuple[str, str]] = []
    for node in chain:
        message = node.get("message")
        if not message:
            continue
        author = message.get("author") or {}
        role = author.get("role")
        if role not in ("user", "assistant"):
            continue

        metadata = message.get("metadata") or {}
        if metadata.get("is_visually_hidden_from_conversation"):
            continue
        recipient = message.get("recipient")
        if recipient not in (None, "all"):
            continue

        text = _extract_text_from_content(message.get("content"))
        if text:
            turns.append((role, text))

    return turns


# ---------------------------------------------------------------------------
# 2. Classifieur en deux passes
# ---------------------------------------------------------------------------

@dataclass
class ClassificationResult:
    keep: bool
    reason: str


# --- Passe 1 : exclusions "sûres" (travail interne du staff) --------------

_DOC_KEYWORDS = (
    r"rapport|compte[- ]?rendu|certificat|consentement|attestation|"
    r"courrier|lettre|bilan|note\s+(?:de\s+)?service|feuille|fiche|planning|"
    r"demande|e-?mail|courriel|script|collation|cadre\s+juridique|"
    r"ordonnance|document|registre|procuration"
)

_STAFF_DOC_DICTATION = re.compile(
    rf"""(?xi)
    \b(
        r[ée]dige(?:[- ]moi)?|
        r[ée]diger|
        [ée]cris(?:[- ]moi)?|
        pr[ée]pare[rz]?(?:[- ]moi)?|
        propose(?:[- ]moi)?|
        donne(?:[- ]moi)?|
        mets(?:[- ]moi)?|
        aide(?:[- ]moi)?|
        g[ée]n[èe]re(?:[- ]moi)?|
        fai(?:s|tes|re)(?:[- ]moi)?\s+(?:une?|des)
    )\b.{{0,80}}\b({_DOC_KEYWORDS})\b
    |
    (je\s+veux|j['’]ai\s+besoin\s+d['’]|il\s+me\s+faut)\s+(?:une?|des)\s+
        ({_DOC_KEYWORDS})|
    mod[èe]le\s+de\s+({_DOC_KEYWORDS})|
    exemple\s+de\s+({_DOC_KEYWORDS})|
    ^\s*objet\s*:|
    [ée]crire\s+un\s+e-?mail|
    demande\s+d['’]offre\s+de\s+service|
    message\s+de\s+report|report(?:er)?\s+des?\s+rendez[- ]?vous|
    donne[- ]moi\s+comment\s+g[ée]rer|
    message\s+officiel|
    cr[ée]ation\s+d['’]un\s+registre|registre\s+du?\s+bloc\s+op[ée]ratoire|
    ^\s*lettre\s+m[ée]dicale
    """
)

_STAFF_ON_BEHALF_OF_PATIENT = re.compile(
    r"""(?xi)
    de\s+la\s+part\s+d['’]?(?:un|une)?\s*(patient|patiente|abonn[ée]e?|client|cliente)|
    \bpatient(e)?\s+(a|est|dit|veut|d[ée]sire|souhaite|confirme|a\s+compris)\b|
    \bpatient\s+\w+\s+age\s+\d+|
    \bnotre\s+patient(e)?\b|مريضنا|
    \bpar\s+un\s+patient\b|\bdeja\s+connu\s+que\s+son\b
    """
)

_CLINICAL_DICTATION = re.compile(
    r"""(?xi)
    \b(compte[- ]?rendu|bilan\s+ophtalmologique|consentement|
       certificat\s+m[ée]dical|rapport\s+m[ée]dical|
       pr[ée]l[èe]vement\s+r[ée]alis[ée]|fen[êe]tre\s+th[ée]rapeutique|
       analyse\s+microbiologique|
       تقرير\s+تفصيلي|detailed\s+report|training\s+report)\b
    """
)

_CLINICAL_EXAM_ABBR = re.compile(
    r"\b(OD|OG|AV|CLD|SKIA|R[ée]f\.?|K1|K2|Pachym[ée]trie|MDD)\b"
)

_THIRD_PERSON_PATIENT = re.compile(
    r"""(?xi)
    \b(mr|mme|mlle|monsieur|madame)\b\s*[A-ZÀ-Ý][\w'’-]*
    (\s+[A-ZÀ-Ý][\w'’-]*){0,3}
    .{0,60}\b(âg[ée]e?\s+de|ans\b)
    |
    \bpatient(e)?\b.{0,40}\b(âg[ée]e?\s+de|se\s+pr[ée]sente|pr[ée]sente\s+une|
        consulte\s+pour)\b
    """
)

_CONFRERE_REFERRAL = re.compile(
    r"""(?xi)
    cher\s+confr[èe]re|
    adresser\s+(?:un|une|ce|cette)\s+patient|
    vous\s+adresse\s+(?:ce|cette)\s+patient|
    [àa]\s+l['’]attention\s+du\s+(?:dr|docteur|pr|professeur)|
    pour\s+le\s+confr[èe]re|
    lettre\s+(?:pour|au?)\s+(?:dr|docteur|pr|professeur)|
    sentiments\s+confraternels|salutations\s+confraternelles|
    ton\s+expertise\s+est\s+sollicit[ée]e|
    confier\s+une\s+malade|je\s+t['’]envoie\s+son\s+nom|
    je\s+suis\s+(?:le\s+|la\s+)?(?:dr|docteur|pr|professeur)\.?\s+\w+.{0,40}
        (rhumatologue|m[ée]decin|g[ée]n[ée]raliste|chirurgien|
         p[ée]diatre|cardiologue|dermatologue|orthop[ée]diste|
         neurologue|endocrinologue|gyn[ée]cologue)
    """
)

_CONTENT_PRODUCTION = re.compile(
    r"""(?xi)
    traduis|traduction|traduire|
    l[ée]gende\s+(?:instagram|facebook|post|story)?|
    \bcaption\b|hachtags?|hashtags?|
    logo|
    affiche|panneau|
    corrig\w*[- ]?moi|
    corrig\w*\s+(?:ce|cette|ces)\b|
    cesmots|[àa]\s+corriger\b|
    correction\s+(?:orthographique|de\s+texte)|
    reformul|
    screenshot|
    post\s+(?:instagram|facebook)|
    story\s+instagram|
    style\s+pixar|
    script\s+(?:pour|vid[ée]o)|
    descriptif\s+(?:avec|vid[ée]o)|
    vid[ée]o\s+([ée]ducative|explicative|op[ée]ratoire)|
    description\s+(?:de|pour)\s+(?:la\s+)?vid[ée]o|
    pour\s+(?:le\s+)?youtube|short\s+youtube|vid[ée]o\s+youtube|
    \bqr\s*code\b|\bun\s+qr\b|
    mot\s+personnalis[ée]|
    publicit[ée]|
    Q\s*/\s*R\b|questions?\s+fr[ée]quentes|foire\s+aux\s+questions|\bfaq\b|
    pr[ée]sente\s+une\s+vid[ée]o\s+explicative|
    شكرا\s+للتواصل\s+مع\s+مركز|فريق\s+مركز\s+طب\s+العيون|
    en\s+couleur\s+\w+.{0,20}s[ée]parer|
    (\#\w+[\s\S]{0,50}){2,}|
    partage\s+l['’]histoire\s+de\s+son\s+patient|
    derri[èe]re\s+chaque\s+(?:intervention|op[ée]ration)|
    وراء\s+كل\s+عملية\s+قصة|
    \bmention\s+l[ée]gale?\b|
    ^\s*en\s+(arabe|fran[çc]ais|anglais)\s*$|
    (j['’]aimes?|abonn[ée]s?|followers?|likes?|vues?)\b.{0,40}
        \b(augmenter|booster|acheter|gagner|obtenir)\b|
    \b(augmenter|booster|acheter|gagner|obtenir)\b.{0,40}
        \b(abonn[ée]s?|followers?|likes?|vues?)\b|
    (?:\b(?:j['’]aimes?|likes?|vues?|abonn[ée]s?|followers?)\b[\s\S]{0,60}){2,}
        [\s\S]{0,100}\b(service|tariffs?)\b
    """
)

_LEGAL_RESEARCH = re.compile(
    r"""(?xi)
    \bloi\b|jurisprudence|code\s+p[ée]nal|cndp|secret\s+m[ée]dical|
    \btpi\b|cour\s+d['’]appel|article\s+\d+|d[ée]ontologi|
    cadre\s+juridique|protection\s+des\s+donn[ée]es\s+personnelles|
    r[èe]glements?\s+[àa]\s+suivre
    """
)

_ADMIN_INTERNAL = re.compile(
    r"""(?xi)
    demande\s+de\s+cong[ée]|planning|note\s+(?:de\s+)?service|
    feuille\s+de\s+(?:garde|poste)|plan\s+de\s+travail|
    liste\s+(?:des\s+)?explorations|traçabilit[ée]|
    liste\s+du\s+mat[ée]riel|mat[ée]riel\s+(?:ophtalmologique|disponible)|
    registre\s+du?\s+bloc\s+op[ée]ratoire|cr[ée]ation\s+d['’]un\s+registre|
    (modification|mise\s+[àa]\s+jour).{0,20}tarifs?|
    liste\s+des\s+tarifs|tarifs?\s*[–-]\s*cabinet|
    r[ôo]les?\s+et\s+responsabilit[ée]s|
    r[ée]sum[ée]\s+de\s+la\s+journ[ée]e|
    avis\s+(?:important\s+)?[àa]\s+nos\s+patients|
    nous\s+tenons\s+[àa]\s+vous\s+informer|nous\s+(?:vous\s+)?informons\s+que|
    cher\s*\(?s?e?s?\)?\s*patient|
    panne\s+(?:de|technique)|hors\s+service|إشعار.{0,15}عطل|عطل\s+تقني|
    نحيطكم\s+علما|service\s+technique.{0,20}intervention|
    mon\s+secr[ée]tariat|notre\s+secr[ée]tariat|
    \bA\s+(arranger|arrager|ex[ée]cuter|ajuster|am[ée]liorer|transformer)\b|
    marketing\s+digital|d[ée]veloppement\s+au\s+cabinet|
    faire\s+une\s+strat[ée]gie|
    image\s+du\s+brand|construire\s+l['’]image|
    ligne\s+directive\s+de\s+communication|\bbranding\b|
    salle\s+(?:de\s+)?chirurgie|retard\s+(?:au|du)\s+d[ée]marrage|
    ressource\s+(?:humaine\s+)?d[ée]di[ée]e|
    r[ée]clamations\s+concernant|nombreuses\s+r[ée]clamations|
    am[ée]liorer\s+la\s+gestion\s+des\s+r[ée]ponses|
    bracelets?\s+(?:bleu|blanc|rouge)|codification\s+des\s+bracelets|
    mettre\s+strat[ée]gie|strat[ée]gie\s+\d{4}|priorit[ée]\s+\d{4}|
    absence\s+de\s+comp[ée]tition|march[ée]\s+vide|
    changement\s+de\s+techniques?\s+de\s+communication|
    meilleure\s+relation\s+patient|points?\s+cl[ée]s?\s+pour|
    agis\s+comme\s+(?:un|une)\s+\w+|
    quelles?\s+sont\s+les\s+questions\s+[àa]\s+poser\s+[àa]\s+un\s+patient|
    t[ée]l[ée]travail|
    validation\s+des\s+comptes[- ]?rendus|
    r[ée]daction\s+des\s+courriers|
    \[\d{1,2}/\d{1,2}\s+\d{1,2}:\d{2}\]
    """
)

_JOB_APPLICATION = re.compile(
    r"""(?xi)
    candidature|curriculum\s+vitae|\bC\.?V\.?\b.{0,25}(pi[èe]ce\s+jointe|ci-joint)|
    pi[èe]ce\s+jointe.{0,20}\bC\.?V\.?\b|
    stage\s+de\s+pr[ée]-?embauche|demande\s+d['’]emploi|
    entretien\s+d['’]embauche|orthoptiste\s+dipl[ôo]m[ée]e?|
    solliciter\s+votre\s+haute\s+bienveillance|
    recherche\s+d['’]un\s+stage|poste\s+d['’]orthoptiste|
    lettre\s+(?:de\s+)?motivation
    """
)

_GENERIC_AUDIENCE_REPLY = re.compile(
    r"""(?xi)
    r[ée]pondre\s+gentiment|
    r[ée]pondre\b.{0,40}\b(aux?\s+)?(personnes|gens|abonn[ée]s|clients|followers)\b
    """
)

_MEDICAL_KNOWLEDGE_QUERY = re.compile(
    r"""(?xi)
    diagnostic\s+diff[ée]rentiel|
    interpr[ée]te(?:r)?\s+(?:cette|ce|cet)\s+(?:oct|image|angiographie)|
    quelles?\s+sont\s+les\s+causes|
    p[âa]leur\s+papillaire|
    analyse\s+(?:du\s+)?(?:fond\s+d['’]œil|oct)|
    \ballaitement\b.{0,20}\bet\b
    """
)

_GREETING_ONLY = re.compile(
    r"""(?xi)^\s*
    (as-?salamu?\s*alaykum|salam\s*(aleykoum|alaykoum)?|
     wa\s*alaykum|assalamu?\s*alaikum|السلام\s*عليكم|
     bonjour|bonsoir|salut|hello|hi)\s*[.!؟?]*\s*$
    """
)

# Sujets gérés ailleurs par le cabinet : on les exclut sur demande, même
# quand le message vient bien d'un vrai patient (1ère personne).
_RDV_TOPIC = re.compile(
    r"""(?xi)
    rendez[- ]?vous|\brdv\b|
    prendre\s+(un\s+)?rendez|confirmer\s+(mon|le|votre)?\s*rendez|
    annuler|annulation|report(er)?\s+(mon|le|votre)?\s*rendez|
    modifier\s+(mon|le)?\s*rendez|vos?\s+disponibilit[ée]s?|cr[ée]neaux?|
    obtenir\s+une\s+consultation|venir\s+pour\s+une\s+consultation|
    m['’]indiquer\s+(vos?\s+)?disponibilit|
    d[ée]marche\s+(à\s+suivre\s+)?pour\s+(obtenir|avoir)\s+une\s+consultation|
    conditions\s+de\s+paiement|
    موعد|حجز\s+موعد
    """
)

_PRICE_TOPIC = re.compile(
    r"""(?xi)
    \bprix\b|\btarifs?\b|\bcombien\b|co[ûu]t\b|\bdevis\b|estimation|
    \bquotation\b|\bquote\b|\bcost\b|\bpricing\b|\bfee\b|installment|
    مصاريف|مصروف|تكلفة|تكاليف|كلفة|
    ثمن|تمن|كم.{0,10}(تمن|ثمن)|كم\s*تتكلف|كم\s*يكلف|
    شحال\w*.{0,40}(فلوس|درهم|تمن|ثمن|تقام|كيكلف|يكلف|تكلف|كتحتاج|تكلفة)|
    (فلوس|درهم|تمن|ثمن|تكلف).{0,40}شحال|
    \b(taman|chhal|hchal)\b
    """
)

_REFERRAL_REQUEST = re.compile(
    r"""(?xi)
    (connaissez[- ]vous|conna[iî]triez[- ]vous)\b.{0,30}\b(docteur|dr|m[ée]decin|sp[ée]cialiste)|
    pouvez[- ]vous\s+(me\s+)?recommander|
    recommandation\s+d['’]un\s+(confr[èe]re|sp[ée]cialiste|m[ée]decin)|
    هل\s+تعرفون?\s+(دكتور|طبيب)\s+مختص
    """
)

# Demande purement logistique (comment vous joindre), sans question médicale
# -- gérée ailleurs, comme les rendez-vous.
_CONTACT_REQUEST_TOPIC = re.compile(
    r"""(?xi)
    n[uú]m[ée]ro\s+de\s+(t[ée]l[ée]phone|tlf|tel)\b|
    arrive\s+pas\s+[àa]\s+(vous\s+)?joindre|
    n['’]arrive\s+pas\s+[àa]\s+(vous\s+)?(joindre|contacter)|
    ^\s*adresse\s+du\s+cabinet\s*$|
    votre\s+num[ée]ro\b|
    num[ée]ro\b.{0,20}\badresse\b|adresse\b.{0,20}\bnum[ée]ro\b
    """
)

PASS1_RULES: list[tuple[str, re.Pattern]] = [
    ("STAFF_DOC_DICTATION", _STAFF_DOC_DICTATION),
    ("STAFF_ON_BEHALF_OF_PATIENT", _STAFF_ON_BEHALF_OF_PATIENT),
    ("CLINICAL_DICTATION", _CLINICAL_DICTATION),
    ("CONFRERE_REFERRAL", _CONFRERE_REFERRAL),
    ("THIRD_PERSON_PATIENT_DESC", _THIRD_PERSON_PATIENT),
    ("CONTENT_PRODUCTION", _CONTENT_PRODUCTION),
    ("LEGAL_RESEARCH", _LEGAL_RESEARCH),
    ("ADMIN_INTERNAL", _ADMIN_INTERNAL),
    ("JOB_APPLICATION", _JOB_APPLICATION),
    ("GENERIC_AUDIENCE_REPLY", _GENERIC_AUDIENCE_REPLY),
    ("MEDICAL_KNOWLEDGE_QUERY", _MEDICAL_KNOWLEDGE_QUERY),
    ("RDV_TOPIC", _RDV_TOPIC),
    ("PRICE_TOPIC", _PRICE_TOPIC),
    ("REFERRAL_REQUEST", _REFERRAL_REQUEST),
    ("CONTACT_REQUEST_TOPIC", _CONTACT_REQUEST_TOPIC),
]


# --- Passe 2 : score fin sur le premier message "survivant" ---------------

_FIRST_PERSON_FR = re.compile(
    r"""(?xi)
    \b(je|j['’]|moi|mon|ma|mes|nous|svp|stp|s['’]il\s+vous\s+pla[iî]t)\b
    """
)

_FIRST_PERSON_AR_DARIJA = re.compile(
    r"""(?x)
    أنا|عندي|بغيت|حابس|خصني|خاصني|خص[هنك]?[يمها]*|دياولي|دیالي|ليا|
    واش|كيفاش|شحال|علاش|شنو|فين|نقدر|أعاني|لديا|لدي\s|أريد|اريد
    """
)

_EYE_CARE_TOPIC = re.compile(
    r"""(?xi)
    lentille|lunette|verre(?:s)?\s+correcteurs?|œil|oeil|yeux|vue|vision|
    glaucome|cataracte|myopie|astigmat|presbytie|conjonctiv|
    k[ée]ratoc[ôo]ne|
    عدسة|عدسات|نظارة|نظارات|عملي[ةا]|عين|عيون|رؤية|بصر|ساد|قرنية|
    جلالة|نظر|شبكية|جحوظ|
    l3ayn\w*|3ayn(?:i|ina|ihom)?|lbasar|basar\b|nadara\w*|3adas\w*
    """
)

_ADDRESS_TO_DOCTOR = re.compile(
    r"""(?xi)
    \b(docteur|dr\.?|cabinet)\b|دكتور|طبيب|بروفيسور|بروفسور
    """
)

_PATIENT_INTENT = re.compile(
    r"""(?xi)
    rendez[- ]?vous|\brdv\b|confirm(?:er|ation)?|
    prix|tarif|combien|co[uû]t|devis|estimation|
    op[ée]ration|chirurgie|intervention|consultation|
    dispo(?:nibilit[ée])?|adresse\s+du\s+cabinet|contact|num[ée]ro|
    t[ée]l[ée]phone|whatsapp|
    ثمن|سعر|عملي[ةا]|موعد|علاج|جراحة|\b(?:ال)?حل\b|\bتمن\b|مشكل[ةه]?|
    douleur|rouge(?:ur)?|gonfl|flou|
    j['’]ai\s+mal|je\s+vois|je\s+sens|mon\s+œil|mon\s+oeil|ma\s+vue
    """
)

_ARABIZI_TOKENS = re.compile(
    r"""(?xi)
    \b(
        ana|bghit|bghina|3?andi|3ndi|3afak|3afek|
        chhal|hchal|dyal|dyali|wach|wch|
        3amaliya|3malia|momkin|n3raf|nqder|n9dr|
        taman|ta9rib\w*|hit|ma3andich|jawabni|3lach|fin|kifach
    )\b
    """
)

_LOW_SUBSTANCE = re.compile(r"^.{0,3}$")


def classify_pass1(first_user_text: str, all_text: str) -> ClassificationResult | None:
    """Renvoie un résultat d'exclusion si une règle "sûre" matche, sinon None
    pour laisser passer la conversation en passe 2."""
    stripped = first_user_text.strip()

    if not stripped:
        return ClassificationResult(False, "EMPTY_OR_NO_USER_TEXT")

    if _GREETING_ONLY.match(stripped) and len(all_text.split()) < 12:
        return ClassificationResult(False, "GREETING_ONLY")

    for reason, pattern in PASS1_RULES:
        if pattern.search(first_user_text):
            return ClassificationResult(False, reason)

    if len(_CLINICAL_EXAM_ABBR.findall(first_user_text)) >= 2:
        return ClassificationResult(False, "CLINICAL_DICTATION")

    return None


def classify_pass2(first_user_text: str) -> ClassificationResult:
    """Score le premier message restant : voix à la 1ère personne + intention
    patient (RDV / prix / symptôme / contact) + adresse au médecin/cabinet."""
    score = 0
    if _FIRST_PERSON_FR.search(first_user_text):
        score += 1
    if _FIRST_PERSON_AR_DARIJA.search(first_user_text):
        score += 1
    if _ADDRESS_TO_DOCTOR.search(first_user_text):
        score += 1
    if _PATIENT_INTENT.search(first_user_text):
        score += 2
    if _EYE_CARE_TOPIC.search(first_user_text):
        score += 1

    arabizi_hits = len({m.group(0).lower() for m in _ARABIZI_TOKENS.finditer(first_user_text)})
    if arabizi_hits >= 2:
        score += 2
    elif arabizi_hits == 1:
        score += 1

    # Pénalité : messages très longs et très structurés ressemblent plus à
    # de la dictée clinique qu'à un message de patient/abonné.
    if len(first_user_text) > 600:
        score -= 1

    if score >= 3:
        return ClassificationResult(True, "KEPT")
    return ClassificationResult(False, "LOW_PATIENT_SIGNAL")


def classify_conversation(turns: list[tuple[str, str]]) -> ClassificationResult:
    first_user_text = next((t for r, t in turns if r == "user"), "")
    all_text = "\n".join(t for _, t in turns)

    result = classify_pass1(first_user_text, all_text)
    if result is not None:
        return result

    return classify_pass2(first_user_text)


# ---------------------------------------------------------------------------
# 3. Anonymisation (noms / adresses)
# ---------------------------------------------------------------------------

_NAME_WITH_TITLE = re.compile(
    r"""(?x)
    \b(Mr|Mme|Mlle|M\.|Dr|Docteur|Monsieur|Madame)\.?\s+
    ([A-ZÀ-Ý][\w'’-]*(?:\s+[A-ZÀ-Ý][\w'’-]*){0,3})
    """
)

_ADDRESS_PATTERN = re.compile(
    r"""(?xi)
    \b(rue|avenue|boulevard|bd|quartier|r[ée]sidence|immeuble|appartement|
       hay|lotissement|angle)\b
    [^\n.,;]{0,60}
    """
)


_STAFF_REFINEMENT_INSTRUCTION = re.compile(
    r"""(?xi)
    ^\s*(
        r[ée]pond(?:s|re)?\b|repondre\b|
        traduis|traduire|traduction|
        en\s+arabe|en\s+fran[çc]ais|en\s+anglais|
        (arabe|fran[çc]ais|anglais)\s*[.!]?\s*$|
        plus\s+(court|long|gentil|bref|simple|professionnel|formel)|
        (courte?|longue?|br[èe]ve?)\s*[.!]?\s*$|
        moins\s+(long|formel)|
        am[ée]liore|corrige|reformul|raccourci|d[ée]taille|d[ée]veloppe|
        sois\s+(plus\s+)?(court|gentil|bref)|
        agit\s+comme|repondre\s+comme|repondre\s+a\s+la\s+mani[èe]re|
        repondre\s+gentiment|
        version\s+(plus\s+)?(courte|longue|formelle)|
        avec\s+(un\s+)?ton|le\s+ton\b|
        rester\s+vague|contacter\s+secr[ée]tariat|ne\s+pas\s+donner|
        ajouter\s+(les?\s+)?num[ée]ros?|rajouter\s+(les?\s+|la\s+)
    )
    """
)


def _is_staff_instruction_turn(text: str) -> bool:
    """Un tour utilisateur ultérieur n'est suivi (ignoré comme faisant
    partie du même échange) que s'il correspond explicitement à une
    instruction de mise en forme de LA MÊME réponse ("traduis-la", "réponds
    plus court", "en arabe"...). Toute autre demande, même courte
    ("numéro whatsapp ?", "cabinet dr rifay", "adresse du cabinet"), est
    considérée comme une nouvelle question et met fin à l'échange : mieux
    vaut garder la première réponse pertinente que dériver vers un sujet
    sans rapport plus loin dans un fil réutilisé par le staff."""
    stripped = text.strip()
    return bool(
        len(stripped.split()) <= 25 and _STAFF_REFINEMENT_INSTRUCTION.search(stripped)
    )


_RESPONSE_DIVIDER = re.compile(r"^[ \t]*[-—⸻*_]{3,}[ \t]*$", re.MULTILINE)

_RESPONSE_PREAMBLE = re.compile(
    r"""(?xi)
    ^\s*(
        voici|voil[àa]|bien\s+s[ûu]r|parfait|tr[èe]s\s+bien|d['’]accord|
        entendu|tamam|طبعا|تمام|بالطبع|مفهوم|
        ✅|👍|👌
    )\b
    """
)

_RESPONSE_TRAILING_META = re.compile(
    r"""(?xi)
    (voulez[- ]vous|souhaitez[- ]vous|veux[- ]tu|tu\s+veux|
     dites[- ]moi|dis[- ]moi|n['’]h[ée]site\s+pas|
     هل\s+تريد|هل\s+تحب|هل\s+ترغب(?:ي|ين)?|أخبرني|تريد\s+أن|
     تحب(?:ي)?\s+ن|بغيتي?\s+ن|تفضلي?\s+ن)
    """
)

# "sans proposer un rendez-vous, sans rien faire" : on retire les blocs de
# contact (téléphone/whatsapp/secrétariat) et les phrases qui invitent le
# patient à prendre/fixer un rendez-vous ou à nous contacter, pour ne garder
# que la réponse médicale à la question posée.
_CONTACT_BLOCK = re.compile(
    r"""(?xi)
    📞|📱|☎|✆|📍|📧|✉|whatsapp|واتساب|secr[ée]tariat|السكرتارية|
    \b0[5-7][\s.-]?\d{2}(?:[\s.-]?\d{2}){3}\b|
    mailto:|@gmail\.com|e-?mail\b|بريد\s+الك?تروني|البريد\s+الإلكتروني
    """
)

_APPOINTMENT_PROPOSAL_LINE = re.compile(
    r"""(?xi)
    (prendre|fixer|r[ée]server|d[ée]terminer|d[ée]finir|proposer)\s*(un\s+)?
        (rendez[- ]?vous|rdv)|
    (rendez[- ]?vous|rdv)\b[\s\S]{0,30}\b(prendre|fixer|r[ée]server)|
    souhaitez[- ]vous\b[\s\S]{0,60}\b(rendez[- ]?vous|rdv)\b|
    je\s+reste\s+[àa]\s+votre\s+disposition|
    tenir\s+moi\s+.{0,15}courant|
    n['’]h[ée]sitez\s+pas\s+[àa]\s+nous\s+contacter|
    nous\s+(vous\s+)?invitons\s+[àa]\s+(nous\s+)?contacter|
    je\s+vous\s+recommande\s+de\s+(prendre\s+rendez|venir\s+en\s+consultation)|
    venir\s+en\s+consultation|
    contactez[- ]nous|nous\s+contacter\s+(pour|au)|
    contacter\s+(directement\s+)?(le\s+cabinet|notre\s+secr[ée]tariat)|
    لحجز\s+موعد|حجز\s+موعد|مرحبا\s+بك\s+لحجز|تحديد\s+موعد|حدد\s+موعد|
    حجز.{0,20}موعد|موعد.{0,20}حجز|أخذ.{0,15}(?:ال)?موعد|
    نعطي[كه]?م?.{0,15}موعد|نعطيك\s+موعد|
    ندعوكم\s+للتواصل|تواصلوا?\s+معنا|
    لا\s+تتردد(?:وا)?\s+في\s+الاتصال|سنكون\s+سعداء\s+بخدمتك|
    يمكنكم?\s+(?:ال)?(?:اتصال|تواصل)\b.{0,30}(?:لحجز|موعد)
    """
)


def strip_appointment_proposal(text: str) -> str:
    """Retire les blocs de contact (téléphone/whatsapp/secrétariat) et les
    phrases qui proposent de prendre/fixer un rendez-vous, pour ne garder
    que la réponse à la question médicale du patient.

    Une proposition peut être : (a) une phrase isolée noyée dans un
    paragraphe qui contient par ailleurs une vraie réponse médicale -- dans
    ce cas on ne retire QUE cette ligne, pour ne pas perdre le reste de la
    réponse ; ou (b) tout un petit paragraphe de clôture (puces, questions
    courtes du style "souhaitez-vous un RDV ? ou une explication ?") qui
    n'est que ça -- dans ce cas on le retire en bloc, sinon des fragments
    de puces orphelins resteraient. On distingue les deux cas par la
    longueur du paragraphe : un paragraphe court est presque toujours un
    bloc de clôture dédié, un paragraphe long mêle proposition et contenu
    médical réel."""
    paragraphs = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]

    without_contact_blocks = [p for p in paragraphs if not _CONTACT_BLOCK.search(p)]
    if without_contact_blocks:
        paragraphs = without_contact_blocks

    cleaned_paragraphs = []
    for para in paragraphs:
        flat = " ".join(para.split("\n"))
        if len(para) <= 220 and _APPOINTMENT_PROPOSAL_LINE.search(flat):
            continue
        lines = [
            ln for ln in para.split("\n") if not _APPOINTMENT_PROPOSAL_LINE.search(ln)
        ]
        if lines:
            cleaned_paragraphs.append("\n".join(lines).strip())

    cleaned = "\n\n".join(p for p in cleaned_paragraphs if p.strip())
    return cleaned or text.strip()

_META_ONLY_RESPONSE = re.compile(
    r"""(?xi)
    ^\s*(bien\s+s[ûu]r|parfait|tr[èe]s\s+bien|d['’]accord|entendu|tamam|
         تمام|طبعا)\b[^.\n]{0,100}
    \b(je\s+vais|j['’]int[èe]gre|سأقوم|راه?\s+غادي)\b
    """
)


_QUOTED_SUGGESTED_REPLY = re.compile(
    r'[:：]\s*\n*\s*["“]([^"“”]{25,}?)["”]', re.DOTALL
)


_PRIVATE_USE_CHARS = re.compile(r"[-]")
_CITATION_ARTIFACT = re.compile(r"\s*(?:cite)?(?:turn\d+search\d+)+", re.I)


def clean_ai_response(text: str) -> str:
    """Nettoie la réponse de l'IA : ne garde que le message destiné au
    patient, en retirant le préambule ("Voici une proposition...") et les
    questions de suivi adressées au staff ("Voulez-vous que je...?")."""
    # ChatGPT insère parfois des marqueurs de citation invisibles (caractères
    # de la zone d'usage privé Unicode autour de "citeturnXsearchY") pour son
    # rendu de recherche web ; sans mise en forme ils restent comme un
    # charabia inutile pour le patient.
    text = _PRIVATE_USE_CHARS.sub("", text)
    text = _CITATION_ARTIFACT.sub("", text)
    dividers = list(_RESPONSE_DIVIDER.finditer(text))
    if len(dividers) >= 2:
        inner = text[dividers[0].end() : dividers[-1].start()].strip()
        if inner:
            return inner

    # Cas "voici le message à envoyer : « ... »" : un seul bloc entre
    # guillemets, substantiel, est presque toujours LE message suggéré
    # (le reste est un commentaire du staff, pas destiné au patient).
    quotes = list(_QUOTED_SUGGESTED_REPLY.finditer(text))
    if len(quotes) == 1 and len(quotes[0].group(1).split()) >= 10:
        return quotes[0].group(1).strip()

    paragraphs = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    while (
        paragraphs
        and len(paragraphs[0].split()) <= 15
        and _RESPONSE_PREAMBLE.match(paragraphs[0].strip())
        and "?" not in paragraphs[0]
        and "؟" not in paragraphs[0]
    ):
        paragraphs.pop(0)
    while (
        paragraphs
        and len(paragraphs[-1].split()) <= 40
        and _RESPONSE_TRAILING_META.search(paragraphs[-1])
    ):
        paragraphs.pop()

    cleaned = "\n\n".join(paragraphs).strip()
    return cleaned or text.strip()


_VALEDICTION = re.compile(
    r"""(?xi)
    cordialement|bien\s+cordialement|salutations\s+distingu[ée]es|
    best\s+regards|kind\s+regards|sincerely|respectueusement|
    avec\s+mes\s+salutations|
    مع\s+فائق\s+الاحترام|مع\s+تحياتي
    """
)


def clean_patient_message(text: str) -> str:
    """Retire les instructions/notes internes que le staff a parfois collées
    à la suite du message du patient, dans le même tour ("... \n\nRepondre a
    la maniere dr rifay", ou une longue note de travail après la signature
    d'un e-mail patient)."""
    paragraphs = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]

    # Si le message du patient se termine par une formule de politesse
    # (+ signature), tout ce qui suit dans le même tour est presque
    # toujours une note interne du staff : on coupe net après.
    for idx, para in enumerate(paragraphs):
        if _VALEDICTION.search(para) and idx < len(paragraphs) - 1:
            paragraphs = paragraphs[: idx + 1]
            break

    # Retire les paragraphes correspondant explicitement à un mot-clé
    # d'instruction connu (pas l'heuristique "court + sans salutation", trop
    # agressive ici : une formule de politesse finale légitime ("Best
    # regards,", "Merci d'avance") est aussi courte et sans salutation, mais
    # fait partie du message du patient), en tête comme en fin de message.
    # Un court reliquat (<= 4 mots, ex. une signature "Dr rifay" laissée
    # après une instruction) est retiré une fois le nettoyage principal fait.
    while len(paragraphs) > 1 and _STAFF_REFINEMENT_INSTRUCTION.search(
        paragraphs[0].strip()
    ):
        paragraphs.pop(0)
    while len(paragraphs) > 1 and (
        _STAFF_REFINEMENT_INSTRUCTION.search(paragraphs[-1].strip())
        or len(paragraphs[-1].split()) <= 4
    ):
        paragraphs.pop()

    cleaned = "\n\n".join(paragraphs).strip()
    return cleaned or text.strip()


def extract_clean_exchange(
    turns: list[tuple[str, str]],
) -> tuple[str, str | None] | None:
    """Isole l'échange patient <-> IA "propre" d'une conversation retenue :
    le message du patient (1er tour "user", pas forcément le tout premier
    tour : certains fils commencent par un message d'accueil de l'IA) et la
    réponse finale, en ignorant les instructions internes du staff pour
    peaufiner la réponse ("traduis-la", "réponds plus court", "en arabe"...)
    et en s'arrêtant dès qu'un message ultérieur ne ressemble plus à une
    telle instruction (nouveau sujet / message sans rapport plus loin dans
    le même fil)."""
    patient_idx = next((i for i, (role, _) in enumerate(turns) if role == "user"), None)
    if patient_idx is None:
        return None

    patient_text = clean_patient_message(turns[patient_idx][1])
    last_assistant_text: str | None = None
    last_substantive_assistant_text: str | None = None
    just_saw_instruction = True  # le 1er tour assistant suit directement le patient

    for role, text in turns[patient_idx + 1 :]:
        if role == "assistant":
            if last_assistant_text is not None and not just_saw_instruction:
                # 2 tours assistant d'affilée sans instruction du staff entre
                # les deux : un tour utilisateur invisible (image, pièce
                # jointe...) a changé de sujet entre-temps. On s'arrête sur
                # la réponse précédente plutôt que de dériver sur ce sujet.
                break
            last_assistant_text = text
            if not _META_ONLY_RESPONSE.match(text.strip()):
                last_substantive_assistant_text = text
            just_saw_instruction = False
            continue
        # role == "user"
        if _is_staff_instruction_turn(text):
            just_saw_instruction = True
            continue
        break

    final_text = last_substantive_assistant_text or last_assistant_text
    if final_text is None:
        return None
    assistant_text = clean_ai_response(final_text)
    if assistant_text:
        assistant_text = strip_appointment_proposal(assistant_text)

    return patient_text, assistant_text


def anonymize(text: str) -> str:
    def _replace_name(m: re.Match) -> str:
        return f"{m.group(1)} [NOM]"

    text = _NAME_WITH_TITLE.sub(_replace_name, text)
    text = _ADDRESS_PATTERN.sub("[ADRESSE]", text)
    return text


# ---------------------------------------------------------------------------
# 4. Orchestration : parcours de tous les fichiers, écriture des sorties
# ---------------------------------------------------------------------------

@dataclass
class KeptConversation:
    conv_id: str
    title: str
    source_file: str
    turns: list[tuple[str, str]]
    first_message_preview: str


@dataclass
class RunStats:
    total_files: int = 0
    total_conversations: int = 0
    kept: int = 0
    duplicates_skipped: int = 0
    exclusion_reasons: Counter = field(default_factory=Counter)


def process(input_dir: Path) -> tuple[list[KeptConversation], RunStats]:
    stats = RunStats()
    kept: list[KeptConversation] = []
    seen_ids: set[str] = set()

    files = find_conversation_files(input_dir)
    stats.total_files = len(files)
    if not files:
        print(f"Aucun fichier 'conversations*.json' trouvé dans {input_dir}", file=sys.stderr)

    for path in files:
        try:
            conversations = load_conversations(path)
        except (ValueError, json.JSONDecodeError) as exc:
            print(f"AVERTISSEMENT: impossible de lire {path}: {exc}", file=sys.stderr)
            continue

        for conv in conversations:
            stats.total_conversations += 1
            conv_id = conv.get("conversation_id") or conv.get("id") or ""

            if conv_id and conv_id in seen_ids:
                stats.duplicates_skipped += 1
                stats.exclusion_reasons["DUPLICATE"] += 1
                continue
            if conv_id:
                seen_ids.add(conv_id)

            turns = linearize_conversation(conv)
            result = classify_conversation(turns)

            if not result.keep:
                stats.exclusion_reasons[result.reason] += 1
                continue

            stats.kept += 1
            first_user_text = next((t for r, t in turns if r == "user"), "")
            preview = anonymize(first_user_text)[:150].replace("\n", " ")
            kept.append(
                KeptConversation(
                    conv_id=conv_id,
                    title=conv.get("title") or "(sans titre)",
                    source_file=path.name,
                    turns=turns,
                    first_message_preview=preview,
                )
            )

    return kept, stats


def filter_kept_with_exchange(
    kept: list[KeptConversation],
) -> list[tuple[KeptConversation, tuple[str, str | None]]]:
    """Ne garde que les conversations pour lesquelles on peut extraire un
    échange patient/IA exploitable (message patient + au moins une réponse
    IA) -- élimine les doublons à réponse vide."""
    result = []
    for conv in kept:
        exchange = extract_clean_exchange(conv.turns)
        if exchange is None or exchange[1] is None:
            continue
        result.append((conv, exchange))
    return result


def write_txt(
    kept_with_exchange: list[tuple[KeptConversation, tuple[str, str | None]]],
    output_path: Path,
) -> None:
    separator = "=" * 80

    with output_path.open("w", encoding="utf-8") as f:
        for i, (conv, (patient_text, assistant_text)) in enumerate(kept_with_exchange):
            if i > 0:
                f.write(separator + "\n")
            f.write(f"CONVERSATION {i + 1}/{len(kept_with_exchange)}\n")
            f.write(f"Titre     : {conv.title}\n")
            f.write(f"ID        : {conv.conv_id}\n")
            f.write(f"Fichier   : {conv.source_file}\n")
            f.write("-" * 80 + "\n")

            f.write(f"[DEMANDE DU PATIENT]\n{anonymize(patient_text)}\n\n")
            f.write(f"[REPONSE DE L'IA]\n{anonymize(assistant_text)}\n\n")


def write_csv(kept: list[KeptConversation], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "titre", "fichier_source", "apercu_premier_message"])
        for conv in kept:
            writer.writerow([conv.conv_id, conv.title, conv.source_file, conv.first_message_preview])


def print_stats(stats: RunStats) -> None:
    print("=== Statistiques ===")
    print(f"Fichiers traités          : {stats.total_files}")
    print(f"Conversations totales     : {stats.total_conversations}")
    print(f"Conversations retenues    : {stats.kept}")
    print(f"Doublons ignorés          : {stats.duplicates_skipped}")
    print("Répartition des exclusions :")
    for reason, count in stats.exclusion_reasons.most_common():
        print(f"  - {reason:<28}: {count}")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir", type=Path, default=Path("./data"),
        help="Dossier contenant les fichiers conversations*.json (recherche récursive)",
    )
    parser.add_argument(
        "--output-txt", type=Path, default=Path("patient_conversations.txt"),
        help="Fichier de sortie .txt avec les conversations retenues",
    )
    parser.add_argument(
        "--output-csv", type=Path, default=Path("patient_conversations_review.csv"),
        help="Fichier CSV de contrôle pour vérification manuelle",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if not args.input_dir.exists():
        print(f"Erreur: le dossier {args.input_dir} n'existe pas.", file=sys.stderr)
        return 1

    kept, stats = process(args.input_dir)
    kept_with_exchange = filter_kept_with_exchange(kept)
    dropped_empty = len(kept) - len(kept_with_exchange)
    stats.kept = len(kept_with_exchange)
    if dropped_empty:
        stats.exclusion_reasons["EMPTY_ANSWER_DROPPED"] += dropped_empty

    write_txt(kept_with_exchange, args.output_txt)
    write_csv([conv for conv, _ in kept_with_exchange], args.output_csv)
    print_stats(stats)
    print(f"\nFichier texte : {args.output_txt}")
    print(f"Fichier CSV   : {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
