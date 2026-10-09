import io

from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas


def generate_certificate_pdf(submission):
    """Render a simple certificate PDF for a passed Submission and attach it.

    Certificates have no verification ID/QR code and no sequential numbering
    per the design decisions in CLAUDE.md.
    """
    from .models import Certificate

    buffer = io.BytesIO()
    page = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)

    student_name = submission.student.get_full_name() or submission.student.username
    course_title = submission.exam.course.title

    page.setFont('Helvetica-Bold', 28)
    page.drawCentredString(width / 2, height - 120, 'Certificate of Completion')

    page.setFont('Helvetica', 14)
    page.drawCentredString(width / 2, height - 180, 'This is to certify that')

    page.setFont('Helvetica-Bold', 24)
    page.drawCentredString(width / 2, height - 220, student_name)

    page.setFont('Helvetica', 14)
    page.drawCentredString(width / 2, height - 260, 'has successfully completed the course')

    page.setFont('Helvetica-Bold', 20)
    page.drawCentredString(width / 2, height - 300, course_title)

    page.setFont('Helvetica', 12)
    page.drawCentredString(
        width / 2, height - 340,
        f'Score: {submission.score}%  |  Issued by Egalitarian Computers',
    )

    page.showPage()
    page.save()

    certificate, _ = Certificate.objects.get_or_create(submission=submission)
    if certificate.pdf_file:
        certificate.pdf_file.delete(save=False)
    certificate.pdf_file.save(
        f'certificate-{submission.exam.course.slug}-{submission.student.username}.pdf',
        ContentFile(buffer.getvalue()),
        save=True,
    )
    return certificate
