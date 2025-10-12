import pdfkit
from django.db.models import Sum
from .models import ExamResult
from decouple import config


def generate_marksheet_html(student, exam, results):
    """Generate HTML content for marksheet certificate PDF"""
    # Calculate totals
    total_marks = sum(float(r.total_marks) for r in results)
    obtained_marks = sum(float(r.marks_obtained or 0) for r in results)
    percentage = (obtained_marks / total_marks * 100) if total_marks > 0 else 0

    # Determine grade
    if percentage >= 91:
        grade = "A+"
    elif percentage >= 81:
        grade = "A"
    elif percentage >= 71:
        grade = "B+"
    elif percentage >= 61:
        grade = "B"
    elif percentage >= 51:
        grade = "C+"
    elif percentage >= 41:
        grade = "C"
    elif percentage >= 33:
        grade = "D"
    else:
        grade = "F"

    result_status = "Pass" if percentage >= 33 else "Fail"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Marksheet - {student.user.get_full_name()}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                line-height: 1.6;
            }}
            .header {{
                text-align: center;
                border: 3px solid #333;
                padding: 20px;
                margin-bottom: 30px;
            }}
            .school-name {{
                font-size: 28px;
                font-weight: bold;
                margin-bottom: 10px;
            }}
            .certificate-title {{
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 10px;
            }}
            .session-info {{
                font-size: 16px;
                margin-bottom: 10px;
            }}
            .student-details {{
                margin-bottom: 30px;
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
            }}
            .detail-row {{
                display: flex;
            }}
            .detail-label {{
                font-weight: bold;
                width: 150px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 30px;
            }}
            th, td {{
                border: 1px solid #333;
                padding: 8px;
                text-align: center;
            }}
            th {{
                background-color: #f0f0f0;
                font-weight: bold;
            }}
            .summary {{
                background: #f9f9f9;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 30px;
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
            }}
            .footer {{
                margin-top: 50px;
                display: flex;
                justify-content: space-between;
            }}
            .signature {{
                width: 200px;
                text-align: center;
                border-top: 1px solid #333;
                padding-top: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="school-name">{config('SCHOOL_NAME', default='SCHOOL')}</div>
            <div class="certificate-title">MARKSHEET</div>
            <div class="session-info">Academic Session: {exam.term.academic_session.year}</div>
        </div>

        <div class="student-details">
            <div class="detail-row">
                <span class="detail-label">Student Name:</span>
                <span>{student.user.get_full_name()}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Roll No:</span>
                <span>{student.roll_no}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Admission No:</span>
                <span>{student.admission_no}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Class:</span>
                <span>{student.classroom}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Father's Name:</span>
                <span>{student.father_name}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Mother's Name:</span>
                <span>{student.mother_name}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Date of Birth:</span>
                <span>{student.dob.strftime('%d/%m/%Y') if student.dob else 'N/A'}</span>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>S.No.</th>
                    <th>Subject</th>
                    <th>Max Marks</th>
                    <th>Min Marks</th>
                    <th>Marks Obtained</th>
                    <th>Grade</th>
                </tr>
            </thead>
            <tbody>
    """

    for i, result in enumerate(results, 1):
        html += f"""
                <tr>
                    <td>{i}</td>
                    <td>{result.subject}</td>
                    <td>{result.total_marks}</td>
                    <td>34</td>
                    <td>{result.marks_obtained or 'N/A'}</td>
                    <td>{result.grade or 'N/A'}</td>
                </tr>
        """

    html += f"""
            </tbody>
        </table>

        <div class="summary">
            <div><strong>Total Marks:</strong> {total_marks:.0f}</div>
            <div><strong>Obtained Marks:</strong> {obtained_marks:.0f}</div>
            <div><strong>Percentage:</strong> {percentage:.2f}%</div>
            <div><strong>Grade:</strong> {grade}</div>
            <div><strong>Result:</strong> {result_status}</div>
        </div>

        <div class="footer">
            <div class="signature">
                <div>Checked By</div>
            </div>
            <div class="signature">
                <div>Controller of Exam</div>
            </div>
            <div class="signature">
                <div>Principal</div>
            </div>
        </div>
    </body>
    </html>
    """

    return html


def generate_annual_result_sheet_html(classroom, exam, results_by_student):
    """Generate HTML content for annual result sheet PDF"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Annual Result Sheet - {classroom}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                line-height: 1.6;
            }}
            .header {{
                text-align: center;
                border: 3px solid #333;
                padding: 20px;
                margin-bottom: 30px;
            }}
            .school-name {{
                font-size: 28px;
                font-weight: bold;
                margin-bottom: 10px;
            }}
            .title {{
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 10px;
            }}
            .session-info {{
                font-size: 16px;
                margin-bottom: 10px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 30px;
            }}
            th, td {{
                border: 1px solid #333;
                padding: 6px;
                text-align: center;
                font-size: 12px;
            }}
            th {{
                background-color: #f0f0f0;
                font-weight: bold;
            }}
            .footer {{
                margin-top: 50px;
                display: flex;
                justify-content: space-between;
            }}
            .signature {{
                width: 200px;
                text-align: center;
                border-top: 1px solid #333;
                padding-top: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="school-name">{config('SCHOOL_NAME', default='SCHOOL')}</div>
            <div class="title">ANNUAL RESULT SHEET</div>
            <div class="session-info">Class: {classroom} | Academic Session: {exam.term.academic_session.year}</div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>S.No.</th>
                    <th>Admission / Roll No.</th>
                    <th>Student Name</th>
                    <th>Total Marks</th>
                    <th>Obtained Marks</th>
                    <th>Result</th>
                    <th>Percentage</th>
                    <th>Rank</th>
                    <th>Signature of Parents</th>
                </tr>
            </thead>
            <tbody>
    """

    # Sort students by total marks (descending) for ranking
    sorted_students = sorted(
        results_by_student.items(), key=lambda x: x[1]["obtained_marks"], reverse=True
    )

    for rank, (student, data) in enumerate(sorted_students, 1):
        result_status = "Pass" if data["percentage"] >= 33 else "Fail"
        html += f"""
                <tr>
                    <td>{rank}</td>
                    <td>{student.roll_no}</td>
                    <td>{student.user.get_full_name()}</td>
                    <td>{data['total_marks']:.0f}</td>
                    <td>{data['obtained_marks']:.0f}</td>
                    <td>{result_status}</td>
                    <td>{data['percentage']:.1f}%</td>
                    <td>{rank}</td>
                    <td></td>
                </tr>
        """

    html += """
            </tbody>
        </table>

        <div class="footer">
            <div class="signature">
                <div>Checked By</div>
            </div>
            <div class="signature">
                <div>Controller of Exam</div>
            </div>
            <div class="signature">
                <div>Principal</div>
            </div>
        </div>
    </body>
    </html>
    """

    return html


def generate_marksheet_pdf(student, exam, results):
    """Generate marksheet PDF for a student"""
    html_content = generate_marksheet_html(student, exam, results)
    pdf_buffer = pdfkit.from_string(
        html_content,
        False,
        options={
            "page-size": "A4",
            "margin-top": "0.5in",
            "margin-right": "0.5in",
            "margin-bottom": "0.5in",
            "margin-left": "0.5in",
        },
    )
    return pdf_buffer


def generate_annual_result_sheet_pdf(classroom, exam, results_by_student):
    """Generate annual result sheet PDF for a class"""
    html_content = generate_annual_result_sheet_html(
        classroom, exam, results_by_student
    )
    pdf_buffer = pdfkit.from_string(
        html_content,
        False,
        options={
            "page-size": "A4",
            "margin-top": "0.5in",
            "margin-right": "0.5in",
            "margin-bottom": "0.5in",
            "margin-left": "0.5in",
            "orientation": "landscape",
        },
    )
    return pdf_buffer


def calculate_student_results(student, exam):
    """Calculate total marks, obtained marks, and percentage for a student in an exam"""
    results = ExamResult.objects.filter(
        student=student,
        exam=exam,
        status=ExamResult.Status.PUBLISHED,
    )

    if not results.exists():
        return None

    total_marks = sum(float(r.total_marks) for r in results)
    obtained_marks = sum(float(r.marks_obtained or 0) for r in results)
    percentage = (obtained_marks / total_marks * 100) if total_marks > 0 else 0

    return {
        "total_marks": total_marks,
        "obtained_marks": obtained_marks,
        "percentage": percentage,
        "results": results,
    }


def get_class_results_summary(classroom, exam):
    """Get results summary for all students in a class for an exam"""
    students = classroom.student.all()
    results_by_student = {}

    for student in students:
        student_results = calculate_student_results(student, exam)
        if student_results:
            results_by_student[student] = student_results

    return results_by_student
