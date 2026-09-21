import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path

from scripts.eml_to_org import convert


class ConvertTest(unittest.TestCase):
    def test_converts_thread_and_org_attachments_without_overwriting(self):
        message = EmailMessage()
        message["Subject"] = "SIA: Website Analytics / Audit"
        message["Date"] = "Tue, 09 Sep 2025 14:30:00 +0100"
        message["From"] = "Analyst <analyst@example.com>"
        message["To"] = "Client <client@example.com>"
        message["Message-ID"] = "<audit@example.com>"
        message.set_content("Current answer.\n\nOn Mon, 8 Sep 2025, Client wrote:\n> Earlier question.\n")
        message.add_alternative(
            '<p>Current answer.</p><p>On Mon, 8 Sep 2025, Client wrote:</p>'
            '<blockquote><p>Earlier question.</p><p>On Sun, 7 Sep 2025, Analyst wrote:</p>'
            '<blockquote><p>Oldest answer.</p></blockquote></blockquote><img src="cid:chart@example.com">'
            '<a href="https://example.com/contact.vcf"><img src="https://example.com/signature.png"></a>',
            subtype="html",
        )
        html_part = message.get_body(preferencelist=("html",))
        assert html_part is not None
        html_part.add_related(
            b"not-a-real-png",
            maintype="image",
            subtype="png",
            cid="<chart@example.com>",
            filename="Chart Screenshot.png",
        )
        message.add_attachment(
            b"%PDF-test",
            maintype="application",
            subtype="pdf",
            filename="Report Q1.pdf",
        )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "input.eml"
            output_dir = root / "org" / "email"
            source.write_bytes(message.as_bytes())

            result = convert(source, output_dir)
            output = Path(str(result["output"]))
            text = output.read_text()

            self.assertEqual(output.name, "2025-09-09-sia-website-analytics-audit.org")
            self.assertEqual(result["messages"], 3)
            self.assertEqual(result["attachments"], 2)
            self.assertIn("* 2025-09-09 14:30 · Analyst <analyst@example.com>", text)
            self.assertIn("* On Mon, 8 Sep 2025, Client wrote:", text)
            self.assertIn("* On Sun, 7 Sep 2025, Analyst wrote:", text)
            self.assertIn("[[attachment:chart-screenshot.png]]", text)
            self.assertIn("[[attachment:report-q1.pdf][report-q1.pdf]]", text)
            self.assertIn("[[https://example.com/contact.vcf][image]]", text)
            self.assertNotIn("][[[", text)
            self.assertNotIn("#+begin_quote", text)
            self.assertNotIn("#+end_quote", text)

            identifier = next(line.split(maxsplit=1)[1] for line in text.splitlines() if line.startswith(":ID:"))
            attachment_dir = output_dir.parent / ".attach" / identifier[:2] / identifier[2:]
            self.assertEqual(
                sorted(path.name for path in attachment_dir.iterdir()),
                ["chart-screenshot.png", "report-q1.pdf"],
            )
            self.assertIn(f":ID: {identifier}", text)
            self.assertNotIn(":DIR:", text)
            self.assertNotIn("\\\\", text)

            second = convert(source, output_dir)
            self.assertEqual(Path(str(second["output"])).name, "2025-09-09-sia-website-analytics-audit-2.org")


if __name__ == "__main__":
    unittest.main()
