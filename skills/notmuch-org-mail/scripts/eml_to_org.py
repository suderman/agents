#!/usr/bin/env python3
"""Convert an RFC 5322 email into one Org file with Org attachment files."""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
import subprocess
import sys
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime
from email import policy
from email.message import EmailMessage, MIMEPart
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import cast
from urllib.parse import quote

MAX_INPUT_BYTES = 100 * 1024 * 1024
THREAD_MARKER = re.compile(
    r"(?im)^[ \t>]*(?P<label>(?:-{2,}[ \t]*)?(?:original message|forwarded message)(?:[ \t]*-{2,})?|on .{6,}? wrote:)[ \t>]*$"
)


@dataclass(frozen=True)
class Attachment:
    name: str
    content_type: str
    data: bytes
    content_id: str | None


def one_line(value: object, fallback: str = "") -> str:
    text = str(value or "")
    return re.sub(r"\s+", " ", text).strip() or fallback


def slug(value: str, fallback: str = "email", limit: int = 80) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    result = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
    return (result[:limit].rstrip("-") or fallback)


def message_date(message: EmailMessage, source: Path) -> datetime:
    try:
        parsed = parsedate_to_datetime(str(message.get("Date", "")))
        if parsed is not None:
            return parsed
    except (TypeError, ValueError, OverflowError):
        pass
    return datetime.fromtimestamp(source.stat().st_mtime).astimezone()


def part_text(part: EmailMessage | MIMEPart) -> str:
    try:
        content = part.get_content()
        if isinstance(content, str):
            return content
    except (LookupError, UnicodeError):
        pass
    charset = part.get_content_charset() or "utf-8"
    payload = cast(bytes | None, part.get_payload(decode=True))
    return (payload or b"").decode(charset, errors="replace")


def unique_name(candidate: str, used: set[str]) -> str:
    path = Path(candidate)
    stem = slug(path.stem, "attachment", 70)
    suffix = re.sub(r"[^a-zA-Z0-9.]", "", path.suffix.lower())[:12]
    name = f"{stem}{suffix}"
    number = 2
    while name.casefold() in used:
        name = f"{stem}-{number}{suffix}"
        number += 1
    used.add(name.casefold())
    return name


def collect_attachments(message: EmailMessage) -> tuple[list[Attachment], dict[str, str]]:
    attachments: list[Attachment] = []
    cid_names: dict[str, str] = {}
    used: set[str] = set()
    unnamed = 0

    for raw_part in message.walk():
        part = cast(EmailMessage, raw_part)
        if part.is_multipart():
            continue
        content_type = part.get_content_type()
        disposition = part.get_content_disposition()
        if disposition != "attachment" and content_type in {"text/plain", "text/html"}:
            continue

        data = cast(bytes | None, part.get_payload(decode=True)) or b""
        if not data:
            continue
        unnamed += 1
        original = one_line(part.get_filename())
        if not original:
            extension = mimetypes.guess_extension(content_type) or ".bin"
            if extension == ".jpe":
                extension = ".jpg"
            original = f"attachment-{unnamed}{extension}"
        name = unique_name(original, used)
        content_id = one_line(part.get("Content-ID")).strip("<>") or None
        attachments.append(Attachment(name, content_type, data, content_id))
        if content_id:
            cid_names[content_id] = name

    return attachments, cid_names


def replace_cid_links(body: str, cid_names: dict[str, str]) -> str:
    for content_id, name in cid_names.items():
        for encoded in {content_id, quote(content_id, safe="@._-")}:
            body = re.sub(rf"cid:{re.escape(encoded)}", f"attachment:{name}", body, flags=re.IGNORECASE)
    return body


def html_to_org(body: str) -> str:
    result = subprocess.run(
        ["pandoc", "--from=html", "--to=org", "--wrap=none", "--shift-heading-level-by=1"],
        input=body,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(one_line(result.stderr, "pandoc failed to convert the HTML body"))
    converted = re.sub(
        r"\[\[([^\[\]\n]+)\]\[\[\[([^\[\]\n]+)\]\]\]\]",
        r"[[\1][image]]",
        result.stdout.strip(),
    )
    converted = re.sub(r"[ \t]*\\\\[ \t]*(?=\n|$)", "", converted)
    return re.sub(r"\n{3,}", "\n\n", converted)


def plain_to_org(body: str) -> str:
    return re.sub(r"(?m)^(\*+\s|#\+)", r",\1", body).strip()


def message_body(message: EmailMessage, cid_names: dict[str, str]) -> str:
    html_part = message.get_body(preferencelist=("html",))
    if html_part is not None:
        return html_to_org(replace_cid_links(part_text(html_part), cid_names))
    plain_part = message.get_body(preferencelist=("plain",))
    if plain_part is not None:
        return plain_to_org(part_text(plain_part))
    return ""


def clean_quote_wrapper(body: str) -> str:
    lines = [
        line
        for line in body.strip().splitlines()
        if line.strip().lower() not in {"#+begin_quote", "#+end_quote"}
    ]
    return "\n".join(re.sub(r"^> ?", "", line) for line in lines).strip()


def split_thread(body: str) -> list[tuple[str | None, str]]:
    # ponytail: quoted-thread formats are not standardized; add format-specific markers only when a real message fails.
    matches = list(THREAD_MARKER.finditer(body))
    if not matches:
        return [(None, body.strip())]

    sections: list[tuple[str | None, str]] = [(None, body[: matches[0].start()].strip())]
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        label = one_line(re.sub(r"^-{2,}|-{2,}$", "", match.group("label")).strip(), "Earlier message")
        sections.append((label, clean_quote_wrapper(body[match.end() : end])))
    return [(label, text) for label, text in sections if text or label]


def nested_messages(message: EmailMessage) -> list[EmailMessage]:
    nested: list[EmailMessage] = []
    for raw_part in message.walk():
        part = cast(EmailMessage, raw_part)
        if part.get_content_type() != "message/rfc822":
            continue
        payload = part.get_payload()
        if isinstance(payload, list):
            nested.extend(item for item in payload if isinstance(item, EmailMessage))
    return nested


def heading(message: EmailMessage, date: datetime) -> str:
    sender = one_line(message.get("From"), "Unknown sender")
    return f"{date:%Y-%m-%d %H:%M} · {sender}"


def next_output_path(directory: Path, base: str) -> Path:
    candidate = directory / f"{base}.org"
    number = 2
    while candidate.exists():
        candidate = directory / f"{base}-{number}.org"
        number += 1
    return candidate


def org_timestamp(date: datetime) -> str:
    return date.strftime("[%Y-%m-%d %a %H:%M]")


def convert(source: Path, output_dir: Path) -> dict[str, object]:
    source = source.expanduser().resolve(strict=True)
    if not source.is_file():
        raise ValueError("Input is not a file")
    if source.suffix.lower() != ".eml":
        raise ValueError("Input must be an .eml file")
    if source.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("Email exceeds the 100 MB safety limit")

    message = cast(EmailMessage, BytesParser(policy=policy.default).parsebytes(source.read_bytes()))
    subject = one_line(message.get("Subject"), "Untitled email")
    date = message_date(message, source)
    file_base = f"{date:%Y-%m-%d}-{slug(subject)}"
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = next_output_path(output_dir, file_base)

    identifier = str(uuid.uuid4())
    attachments, cid_names = collect_attachments(message)
    sections = split_thread(message_body(message, cid_names))
    rendered_sections: list[str] = []
    outer_heading = heading(message, date)
    attachment_lines = ["*Attachments:*"] + [
        f"- [[attachment:{attachment.name}][{attachment.name}]] ({attachment.content_type})"
        for attachment in attachments
    ]

    for index, (label, body) in enumerate(sections):
        title = outer_heading if index == 0 else one_line(label, "Earlier message")
        properties = f"\n:PROPERTIES:\n:ID: {identifier}\n:END:" if index == 0 else ""
        content = body
        if index == 0 and attachments:
            content = f"{content}\n\n" + "\n".join(attachment_lines)
        rendered_sections.append(f"* {title}{properties}\n\n{content}".rstrip())

    for nested in nested_messages(message):
        nested_date = message_date(nested, source)
        rendered_sections.append(f"* {heading(nested, nested_date)}\n\n{message_body(nested, cid_names)}".rstrip())

    metadata = [
        f"#+title: {subject}",
        f"#+date: {org_timestamp(date)}",
        "#+filetags: :email:",
        f"#+from: {one_line(message.get('From'), 'Unknown')}",
        f"#+to: {one_line(message.get('To'), 'Unknown')}",
    ]
    cc = one_line(message.get("Cc"))
    message_id = one_line(message.get("Message-ID"))
    if cc:
        metadata.append(f"#+cc: {cc}")
    if message_id:
        metadata.append(f"#+message_id: {message_id}")
    metadata.append(f"#+source_file: {source.name}")

    org = "\n".join(metadata) + "\n\n" + "\n\n".join(rendered_sections).strip() + "\n"

    attachment_dir = output_dir.parent / ".attach" / identifier[:2] / identifier[2:]
    try:
        if attachments:
            attachment_dir.mkdir(parents=True, exist_ok=False)
            for attachment in attachments:
                (attachment_dir / attachment.name).write_bytes(attachment.data)
        with output_path.open("x", encoding="utf-8") as handle:
            handle.write(org)
    except Exception:
        if attachment_dir.exists():
            for path in attachment_dir.iterdir():
                path.unlink()
            attachment_dir.rmdir()
        raise

    return {
        "output": str(output_path),
        "attachments": len(attachments),
        "messages": len(rendered_sections),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert an RFC 5322 .eml file into Org with Org attachment files."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path.home() / "org" / "email")
    args = parser.parse_args()
    try:
        print(json.dumps(convert(args.source, args.output_dir)))
    except Exception as error:
        print(f"eml-to-org: {one_line(error)}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
