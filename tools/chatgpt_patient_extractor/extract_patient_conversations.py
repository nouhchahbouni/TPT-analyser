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

_STAFF_DOC_DICTATION = re.compile(
    r"""(?xi)
    \b(
        r[ée]dige(?:[- ]moi)?|
        r[ée]diger|
        [ée]cris(?:[- ]moi)?|
        pr[ée]pare(?:[- ]moi)?|
        propose(?:[- ]moi)?|
        donne(?:[- ]moi)?|
        mets(?:[- ]moi)?|
        aide(?:[- ]moi)?|
        g[ée]n[èe]re(?:[- ]moi)?|
        fai(?:s|tes)(?:[- ]moi)?\s+(?:une?|des)|
        je\s+veux\s+(?:une?|des)\s+(?:lettre|courrier|certificat|rapport|
            compte[- ]?rendu|consentement|attestation|note|demande|fiche)|
        mod[èe]le\s+de|
        exemple\s+de\s+(?:lettre|courrier|certificat|rapport)
    )\b.{0,80}\b(
        rapport|compte[- ]?rendu|certificat|consentement|attestation|
        courrier|lettre|bilan|note\s+de\s+service|feuille|fiche|planning|
        demande|e-?mail|courriel|script|collation|cadre\s+juridique|
        ordonnance
    )\b
    |
    ^\s*objet\s*:|
    [ée]crire\s+un\s+e-?mail|
    demande\s+d['’]offre\s+de\s+service|
    message\s+de\s+report|report(?:er)?\s+des?\s+rendez[- ]?vous|
    donne[- ]moi\s+comment\s+g[ée]rer|
    message\s+officiel
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
    sentiments\s+confraternels|ton\s+expertise\s+est\s+sollicit[ée]e
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
    description\s+de\s+video|
    pour\s+(?:le\s+)?youtube|short\s+youtube|
    \bqr\s*code\b|\bun\s+qr\b|
    mot\s+personnalis[ée]|
    publicit[ée]|
    Q\s*/\s*R\b|questions?\s+fr[ée]quentes|foire\s+aux\s+questions|\bfaq\b|
    pr[ée]sente\s+une\s+vid[ée]o\s+explicative|
    شكرا\s+للتواصل\s+مع\s+مركز|فريق\s+مركز\s+طب\s+العيون
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
    demande\s+de\s+cong[ée]|planning|note\s+de\s+service|
    feuille\s+de\s+(?:garde|poste)|plan\s+de\s+travail|
    liste\s+(?:des\s+)?explorations|traçabilit[ée]|
    (modification|mise\s+[àa]\s+jour).{0,20}tarifs?|
    liste\s+des\s+tarifs|tarifs?\s*[–-]\s*cabinet|
    r[ôo]les?\s+et\s+responsabilit[ée]s|
    r[ée]sum[ée]\s+de\s+la\s+journ[ée]e|
    avis\s+(?:important\s+)?[àa]\s+nos\s+patients|
    nous\s+tenons\s+[àa]\s+vous\s+informer|
    mon\s+secr[ée]tariat|notre\s+secr[ée]tariat|
    \bA\s+(arranger|arrager|ex[ée]cuter|ajuster|am[ée]liorer|transformer)\b|
    marketing\s+digital|d[ée]veloppement\s+au\s+cabinet|
    faire\s+une\s+strat[ée]gie|
    image\s+du\s+brand|construire\s+l['’]image|
    ligne\s+directive\s+de\s+communication|\bbranding\b
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
    واش|كيفاش|شحال|علاش|شنو|فين|نقدر|أعاني|لديا|لدي\s
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
    \b(docteur|dr\.?|cabinet)\b|دكتور|طبيب|بروفيسور
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


def write_txt(kept: list[KeptConversation], output_path: Path) -> None:
    role_label = {"user": "PATIENT", "assistant": "EQUIPE / ASSISTANT IA"}
    separator = "=" * 80

    with output_path.open("w", encoding="utf-8") as f:
        for i, conv in enumerate(kept):
            if i > 0:
                f.write(separator + "\n")
            f.write(f"CONVERSATION {i + 1}/{len(kept)}\n")
            f.write(f"Titre     : {conv.title}\n")
            f.write(f"ID        : {conv.conv_id}\n")
            f.write(f"Fichier   : {conv.source_file}\n")
            f.write("-" * 80 + "\n")
            for turn_num, (role, text) in enumerate(conv.turns, start=1):
                anon_text = anonymize(text)
                label = role_label.get(role, role.upper())
                f.write(f"--- Message {turn_num} [{label}] ---\n{anon_text}\n\n")


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
    write_txt(kept, args.output_txt)
    write_csv(kept, args.output_csv)
    print_stats(stats)
    print(f"\nFichier texte : {args.output_txt}")
    print(f"Fichier CSV   : {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
