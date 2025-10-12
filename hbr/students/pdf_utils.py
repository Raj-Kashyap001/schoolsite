from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing, Circle
from io import BytesIO
import os
from django.conf import settings
from decouple import config


def generate_student_profile_pdf(student_data, user_data):
    """
    Generate a modern PDF student profile document with contemporary design
    using the provided color scheme.

    Args:
        student_data: Dictionary containing student model data
        user_data: Dictionary containing user model data

    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    story = []

    # New Color Palette (Converted from HSL to ReportLab HexColor)
    PRIMARY_COLOR = colors.HexColor("#8F403C")  # hsl(3, 68%, 35%) - Deep Maroon
    SECONDARY_COLOR = colors.HexColor(
        "#F4F9FA"
    )  # hsl(190, 45%, 95%) - Very Light Blue-Gray
    DARK_TEXT = colors.HexColor("#333333")  # hsl(0 0 20) - Dark Gray
    LIGHT_TEXT = colors.HexColor(
        "#9CA3AF"
    )  # Standard ReportLab lighter gray for secondary info
    BORDER_COLOR = colors.HexColor(
        "#E5E7EB"
    )  # Light border (kept the original light gray)

    # --- Typography Styles ---
    school_title_style = ParagraphStyle(
        "SchoolTitle",
        parent=styles["Heading1"],
        fontSize=24,
        spaceAfter=4,  # Reduced space
        alignment=0,
        textColor=PRIMARY_COLOR,  # Changed to primary color
        fontName="Helvetica-Bold",
        leading=28,
    )

    school_subtitle_style = ParagraphStyle(
        "SchoolSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        alignment=0,
        textColor=LIGHT_TEXT,
        spaceAfter=4,  # Reduced space
        leading=14,
    )

    section_header_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=14,
        alignment=0,
        textColor=PRIMARY_COLOR,  # Changed to primary color
        fontName="Helvetica-Bold",
        spaceAfter=8,
        spaceBefore=15,  # Increased space before
    )

    student_name_style = ParagraphStyle(
        "StudentName",
        parent=styles["Heading1"],
        fontSize=20,
        alignment=0,
        textColor=DARK_TEXT,
        fontName="Helvetica-Bold",
        spaceAfter=4,
        leading=24,
    )

    contact_style = ParagraphStyle(
        "Contact",
        parent=styles["Normal"],
        fontSize=9,
        alignment=0,
        textColor=DARK_TEXT,  # Changed to DARK_TEXT for better visibility on secondary bg
        leading=13,
    )

    # --- Header with School Info ---
    story.append(Paragraph(config("SCHOOL_NAME", default="SCHOOL"), school_title_style))
    story.append(
        Paragraph(
            "123 Education Street, Knowledge City - 400001", school_subtitle_style
        )
    )
    story.append(
        Paragraph(
            "Phone: +91-22-1234-5678 | Email: info@stmaryshigh.edu",
            school_subtitle_style,
        )
    )

    # Accent divider (now using PRIMARY_COLOR)
    divider_data = [[""]]
    divider_table = Table(divider_data, colWidths=[6.5 * inch])
    divider_table.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (-1, -1), 2, PRIMARY_COLOR),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(divider_table)
    story.append(Spacer(1, 0.25 * inch))

    # --- Profile Image Handling (Kept Original Logic) ---
    if student_data.get("profile_photo"):
        try:
            # Assuming settings.MEDIA_ROOT and student_data["profile_photo"] exist
            image_path = os.path.join(
                settings.MEDIA_ROOT, str(student_data["profile_photo"])
            )
            if os.path.exists(image_path):
                # Placeholder for actual image creation logic - ReportLab doesn't handle image masking easily
                profile_img = Image(image_path, width=1.2 * inch, height=1.2 * inch)
                profile_img.hAlign = "CENTER"
            else:
                profile_img = Paragraph(
                    '<para align="center" fontSize="8" textColor="#9CA3AF">No Photo</para>',
                    contact_style,
                )
        except Exception:  # Catch broader exceptions during path/image processing
            profile_img = Paragraph(
                '<para align="center" fontSize="8" textColor="#9CA3AF">No Photo</para>',
                contact_style,
            )
    else:
        profile_img = Paragraph(
            '<para align="center" fontSize="8" textColor="#9CA3AF">No Photo</para>',
            contact_style,
        )

    # --- Profile Section Table ---
    student_info = [
        [
            profile_img,
            Paragraph(
                f'<b>{user_data["first_name"]} {user_data["last_name"]}</b>',
                student_name_style,
            ),
        ],
        [
            "",
            Paragraph(
                f'Email: {user_data["email"]}<br/>'
                f'Mobile: {student_data["mobile_no"]}<br/>'
                f'Admission No: {student_data["admission_no"]}',
                contact_style,
            ),
        ],
    ]

    profile_table = Table(student_info, colWidths=[1.5 * inch, 5 * inch])
    profile_table.setStyle(
        TableStyle(
            [
                # Changed background to the new secondary color
                ("BACKGROUND", (0, 0), (-1, -1), SECONDARY_COLOR),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (1, 0), (1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("SPAN", (0, 0), (0, 1)),
                ("LEFTPADDING", (0, 0), (-1, -1), 15),
                ("RIGHTPADDING", (0, 0), (-1, -1), 15),
                ("TOPPADDING", (0, 0), (-1, -1), 15),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 15),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ]
        )
    )
    story.append(profile_table)
    story.append(Spacer(1, 0.3 * inch))

    # --- Student Details Table ---
    story.append(Paragraph("Student Information", section_header_style))

    # Detail data structure remains the same
    details_data = [
        [
            "SR Number",
            str(student_data["sr_no"]),
            "Roll Number",
            str(student_data["roll_no"]),
        ],
        [
            "Father's Name",
            student_data["father_name"],
            "Mother's Name",
            student_data["mother_name"],
        ],
        [
            "Date of Birth",
            student_data["dob"].strftime("%d/%m/%Y") if student_data["dob"] else "N/A",
            "Gender",
            student_data["gender"],
        ],
        [
            "Category",
            student_data["category"] or "General",
            "Class",
            str(student_data["classroom"]),
        ],
        [
            "Stream",
            student_data.get("stream") or "N/A",
            "Weight",
            f"{student_data.get('weight')} kg" if student_data.get("weight") else "N/A",
        ],
        [
            "Height",
            f"{student_data.get('height')} cm" if student_data.get("height") else "N/A",
            "Date Joined",
            user_data["date_joined"].strftime("%d/%m/%Y"),
        ],
        [
            "Subjects",
            student_data.get("subjects") or "N/A",
            "",
            "",
        ],
        [
            "Current Address",
            student_data.get("current_address") or "N/A",
            "",
            "",
        ],
        [
            "Permanent Address",
            student_data.get("permanent_address") or "N/A",
            "",
            "",
        ],
    ]

    details_table = Table(
        details_data, colWidths=[1.5 * inch, 1.75 * inch, 1.5 * inch, 1.75 * inch]
    )
    # Adjust table style for rows with empty cells
    details_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("TEXTCOLOR", (0, 0), (-1, -1), DARK_TEXT),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (1, -1), "LEFT"),
                ("ALIGN", (2, 0), (2, -1), "LEFT"),
                ("ALIGN", (3, 0), (3, -1), "LEFT"),
                # Bold the labels for better visual hierarchy
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                # Use the new secondary color for row banding
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [SECONDARY_COLOR, colors.white]),
                # Span empty cells for full-width rows
                ("SPAN", (1, 5), (3, 5)),  # Subjects row
                ("SPAN", (1, 6), (3, 6)),  # Current Address row
                ("SPAN", (1, 7), (3, 7)),  # Permanent Address row
            ]
        )
    )
    story.append(details_table)
    story.append(Spacer(1, 0.4 * inch))

    # --- Footer ---
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=8,
        alignment=1,  # Center alignment
        textColor=LIGHT_TEXT,
        leading=12,
    )

    story.append(divider_table)  # Re-use the primary-colored divider
    story.append(Spacer(1, 0.15 * inch))

    story.append(
        Paragraph(
            "This is an official student profile document generated by the school management system.",
            footer_style,
        )
    )
    story.append(
        Paragraph(
            f"Generated on: {user_data['date_joined'].strftime('%d %B %Y')}",
            footer_style,
        )
    )

    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_certificate_pdf(student, certificate_type):
    """
    Generate a certificate PDF for a student using HTML template.

    Args:
        student: Student model instance
        certificate_type: CertificateType model instance

    Returns:
        BytesIO buffer containing the PDF
    """
    import pdfkit
    from django.template import Template, Context
    from datetime import datetime

    # Prepare template context
    context = {
        "student_name": student.user.get_full_name(),
        "father_name": student.father_name,
        "mother_name": student.mother_name,
        "class": str(student.classroom),
        "roll_no": student.roll_no,
        "admission_no": student.admission_no,
        "date": datetime.now().strftime("%d %B %Y"),
        "school_name": config("SCHOOL_NAME", default="SCHOOL"),
    }

    # Use HTML template if available, otherwise use default
    if certificate_type.html_template:
        template = Template(certificate_type.html_template)
        html_content = template.render(Context(context))
    else:
        # Default template
        description_html = (
            f'<p class="content">{certificate_type.description}</p>'
            if certificate_type.description
            else ""
        )
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background: #f9f9f9;
                }}
                .certificate {{
                    background: white;
                    padding: 40px;
                    border: 5px solid #8F403C;
                    max-width: 800px;
                    margin: 0 auto;
                }}
                h1 {{
                    color: #8F403C;
                    font-size: 36px;
                    margin-bottom: 20px;
                }}
                .student-name {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #8F403C;
                    margin: 20px 0;
                }}
                .content {{
                    font-size: 18px;
                    line-height: 1.6;
                    margin: 20px 0;
                }}
                .signature {{
                    margin-top: 50px;
                    font-size: 16px;
                }}
            </style>
        </head>
        <body>
            <div class="certificate">
                <h1>{{ school_name }}</h1>
                <h2>Certificate of Achievement</h2>
                <p class="content">This is to certify that</p>
                <p class="student-name">{context['student_name']}</p>
                <p class="content">has successfully completed the requirements for</p>
                <h3>{certificate_type.name}</h3>
                {description_html}
                <p class="content">Issued on: {context['date']}</p>
                <div class="signature">
                    <p>___________________________</p>
                    <p>Principal</p>
                    <p>{{ school_name }}</p>
                </div>
            </div>
        </body>
        </html>
        """

    # Generate PDF from HTML
    options = {
        "page-size": "A4",
        "margin-top": "1in",
        "margin-right": "1in",
        "margin-bottom": "1in",
        "margin-left": "1in",
        "encoding": "UTF-8",
    }

    try:
        pdf_data = pdfkit.from_string(html_content, False, options=options)
        buffer = BytesIO(pdf_data)
        buffer.seek(0)
        return buffer
    except Exception as e:
        # Fallback to ReportLab if pdfkit fails
        print(f"PDFKit failed: {e}, using ReportLab fallback")
        return generate_certificate_pdf_fallback(student, certificate_type)


def generate_certificate_pdf_fallback(student, certificate_type):
    """
    Fallback certificate generation using ReportLab.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    story = []

    # Color Palette
    PRIMARY_COLOR = colors.HexColor("#8F403C")  # Deep Maroon
    DARK_TEXT = colors.HexColor("#333333")

    # Styles
    school_title_style = ParagraphStyle(
        "SchoolTitle",
        parent=styles["Heading1"],
        fontSize=28,
        spaceAfter=10,
        alignment=1,  # Center
        textColor=PRIMARY_COLOR,
        fontName="Helvetica-Bold",
    )

    certificate_title_style = ParagraphStyle(
        "CertificateTitle",
        parent=styles["Heading1"],
        fontSize=24,
        spaceAfter=20,
        alignment=1,
        textColor=PRIMARY_COLOR,
        fontName="Helvetica-Bold",
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=14,
        alignment=1,
        textColor=DARK_TEXT,
        leading=20,
    )

    student_name_style = ParagraphStyle(
        "StudentName",
        parent=styles["Heading1"],
        fontSize=20,
        alignment=1,
        textColor=PRIMARY_COLOR,
        fontName="Helvetica-Bold",
        spaceAfter=10,
    )

    # Header
    story.append(Paragraph(config("SCHOOL_NAME", default="SCHOOL"), school_title_style))
    story.append(Spacer(1, 0.5 * inch))

    # Certificate Title
    story.append(Paragraph(certificate_type.name, certificate_title_style))
    story.append(Spacer(1, 0.5 * inch))

    # Body Text
    story.append(Paragraph("This is to certify that", body_style))
    story.append(Spacer(1, 0.25 * inch))

    # Student Name
    full_name = f"{student.user.first_name} {student.user.last_name}"
    story.append(Paragraph(full_name, student_name_style))

    # Certificate Type Description
    if certificate_type.description:
        story.append(Spacer(1, 0.25 * inch))
        story.append(Paragraph(certificate_type.description, body_style))

    # Date
    from datetime import datetime

    current_date = datetime.now().strftime("%d %B %Y")
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph(f"Issued on: {current_date}", body_style))

    # Signature placeholder
    story.append(Spacer(1, 1 * inch))
    story.append(Paragraph("___________________________", body_style))
    story.append(Paragraph("Principal", body_style))
    story.append(Paragraph(config("SCHOOL_NAME", default="SCHOOL"), body_style))

    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_payment_receipt_pdf(payment):
    """
    Generate a payment receipt PDF.

    Args:
        payment: Payment model instance

    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    story = []

    # Color Palette
    PRIMARY_COLOR = colors.HexColor("#8F403C")  # Deep Maroon
    SECONDARY_COLOR = colors.HexColor("#F4F9FA")  # Light Blue-Gray
    DARK_TEXT = colors.HexColor("#333333")
    LIGHT_TEXT = colors.HexColor("#9CA3AF")

    # Styles
    school_title_style = ParagraphStyle(
        "SchoolTitle",
        parent=styles["Heading1"],
        fontSize=28,
        spaceAfter=10,
        alignment=1,  # Center
        textColor=PRIMARY_COLOR,
        fontName="Helvetica-Bold",
    )

    receipt_title_style = ParagraphStyle(
        "ReceiptTitle",
        parent=styles["Heading1"],
        fontSize=24,
        spaceAfter=20,
        alignment=1,
        textColor=PRIMARY_COLOR,
        fontName="Helvetica-Bold",
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=14,
        alignment=0,
        textColor=DARK_TEXT,
        leading=20,
    )

    # Header
    story.append(Paragraph(config("SCHOOL_NAME", default="SCHOOL"), school_title_style))
    story.append(Spacer(1, 0.5 * inch))

    # Receipt Title
    story.append(Paragraph("Payment Receipt", receipt_title_style))
    story.append(Spacer(1, 0.5 * inch))

    # Receipt Details
    story.append(Paragraph(f"<b>Receipt No:</b> {payment.id}", body_style))
    story.append(
        Paragraph(f"<b>Student:</b> {payment.student.user.get_full_name()}", body_style)
    )
    story.append(Paragraph(f"<b>Roll No:</b> {payment.student.roll_no}", body_style))
    story.append(Paragraph(f"<b>Description:</b> {payment.description}", body_style))
    story.append(Paragraph(f"<b>Amount:</b> ₹{payment.amount}", body_style))
    story.append(Paragraph(f"<b>Status:</b> {payment.status}", body_style))
    if payment.payment_date:
        story.append(
            Paragraph(
                f"<b>Payment Date:</b> {payment.payment_date.strftime('%d %B %Y')}",
                body_style,
            )
        )
    if payment.transaction_id:
        story.append(
            Paragraph(f"<b>Transaction ID:</b> {payment.transaction_id}", body_style)
        )

    # Date
    from datetime import datetime

    current_date = datetime.now().strftime("%d %B %Y")
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph(f"Issued on: {current_date}", body_style))

    # Signature placeholder
    story.append(Spacer(1, 1 * inch))
    story.append(Paragraph("___________________________", body_style))
    story.append(Paragraph("Accounts Department", body_style))
    story.append(Paragraph(config("SCHOOL_NAME", default="SCHOOL"), body_style))

    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer
