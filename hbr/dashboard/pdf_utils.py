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


def generate_student_profile_pdf(student_data, user_data):
    """
    Generate a modern PDF student profile document with contemporary design.

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

    # Modern Color Palette
    PRIMARY_COLOR = colors.HexColor("#3B82F6")
    DARK_TEXT = colors.HexColor("#1F2937")
    LIGHT_BG = colors.HexColor("#F9FAFB")
    BORDER_COLOR = colors.HexColor("#E5E7EB")
    GRAY_TEXT = colors.HexColor("#6B7280")

    # Typography Styles
    school_title_style = ParagraphStyle(
        "SchoolTitle",
        parent=styles["Heading1"],
        fontSize=24,
        spaceAfter=6,
        alignment=0,
        textColor=DARK_TEXT,
        fontName="Helvetica-Bold",
        leading=28,
    )

    school_subtitle_style = ParagraphStyle(
        "SchoolSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        alignment=0,
        textColor=GRAY_TEXT,
        spaceAfter=6,
        leading=14,
    )

    section_header_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=14,
        alignment=0,
        textColor=DARK_TEXT,
        fontName="Helvetica-Bold",
        spaceAfter=10,
        spaceBefore=6,
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
        textColor=GRAY_TEXT,
        leading=13,
    )

    # Header with School Info
    story.append(Paragraph("HBR Public School", school_title_style))
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

    # Accent divider
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

    # Profile Section with smaller rounded image
    if student_data.get("profile_photo"):
        try:
            image_path = os.path.join(
                settings.MEDIA_ROOT, str(student_data["profile_photo"])
            )
            if os.path.exists(image_path):
                # Smaller circular profile image
                profile_img = Image(image_path, width=1.2 * inch, height=1.2 * inch)
                profile_img.hAlign = "CENTER"
            else:
                profile_img = Paragraph(
                    '<para align="center" fontSize="8" textColor="#9CA3AF">No Photo</para>',
                    contact_style,
                )
        except:
            profile_img = Paragraph(
                '<para align="center" fontSize="8" textColor="#9CA3AF">No Photo</para>',
                contact_style,
            )
    else:
        profile_img = Paragraph(
            '<para align="center" fontSize="8" textColor="#9CA3AF">No Photo</para>',
            contact_style,
        )

    # Student info in profile card
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
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
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
    story.append(Spacer(1, 0.25 * inch))

    # Student Details Table
    story.append(Paragraph("Student Information", section_header_style))

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
        ["Date Joined", user_data["date_joined"].strftime("%d/%m/%Y"), "", ""],
    ]

    details_table = Table(
        details_data, colWidths=[1.5 * inch, 1.75 * inch, 1.5 * inch, 1.75 * inch]
    )
    details_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("TEXTCOLOR", (0, 0), (-1, -1), DARK_TEXT),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (1, -1), "LEFT"),
                ("ALIGN", (2, 0), (2, -1), "LEFT"),
                ("ALIGN", (3, 0), (3, -1), "LEFT"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_BG, colors.white]),
            ]
        )
    )
    story.append(details_table)
    story.append(Spacer(1, 0.3 * inch))

    # Footer
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=8,
        alignment=1,
        textColor=GRAY_TEXT,
        leading=12,
    )

    story.append(divider_table)
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
