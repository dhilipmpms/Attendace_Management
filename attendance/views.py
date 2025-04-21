from django.shortcuts import render, redirect, get_object_or_404
from .models import Member, Session, Attendance
from datetime import date, timedelta
from django.core.paginator import Paginator
from django.contrib import messages
import openpyxl
from django.http import HttpResponse,FileResponse
from reportlab.pdfgen import canvas
import io
import xlsxwriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch


def home(request):
    sessions = Session.objects.order_by('-date')[:5]
    return render(request, 'attendance/home.html', {'sessions': sessions})

def add_member(request):
    if request.method == "POST":
        name = request.POST.get('name')
        work = request.POST.get('work')
        phone = request.POST.get('phone')
        if name:
            Member.objects.create(name=name,work=work,phone=phone)
        return redirect('add_member')
    return render(request, 'attendance/add_member.html')

def add_session(request):
    if request.method == "POST":
        name = request.POST.get('name')
        session_date = request.POST.get('date')
        if name and session_date:
            Session.objects.create(name=name, date=session_date)
        return redirect('home')
    return render(request, 'attendance/add_session.html')


def mark_attendance(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    members = Member.objects.all()

    if request.method == "POST":
        present_ids = request.POST.getlist('present_members')

        for member in members:
            is_present = str(member.id) in present_ids
            attendance, _ = Attendance.objects.get_or_create(session=session, member=member)
            attendance.is_present = is_present
            attendance.save()

        messages.success(request, "✅ Attendance successfully updated!")
        return redirect('mark_attendance', session_id=session_id)  # Redirect to same page

    present_ids = Attendance.objects.filter(session=session, is_present=True).values_list('member_id', flat=True)

    return render(request, 'attendance/mark_attendance.html', {
        'session': session,
        'members': members,
        'present_ids': list(present_ids),
    })

def calendar_view(request):
    days = [date.today() - timedelta(days=i) for i in range(0, 30)]
    sessions = Session.objects.all()
    return render(request, 'attendance/calendar.html', {'days': days, 'sessions': sessions})

def attendance_detail(request, date):
    session = Session.objects.filter(date=date).first()

    if not session:
        return render(request, 'attendance/attendance_detail.html', {
            'session': None,
            'attendance_list': [],
            'date': date
        })

    # Handle delete request
    if request.method == "POST" and "delete" in request.POST:
        att_id = request.POST.get("delete")
        Attendance.objects.filter(id=att_id, session=session).delete()
        return redirect('attendance_detail', date=date)

    # Search logic
    search_query = request.GET.get('search', '')
    attendance_list = Attendance.objects.filter(
        session=session,
        is_present=True,
        member__name__icontains=search_query
    ).select_related('member')

    # Pagination
    paginator = Paginator(attendance_list, 50)  # Adjust per page count as needed
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'attendance/attendance_detail.html', {
        'session': session,
        'page_obj': page_obj,
        'search_query': search_query,
        'date': date
    })


def member_list(request):
    # Handle delete request
    if request.method == 'POST' and 'delete' in request.POST:
        member_id = request.POST['delete']
        Member.objects.filter(id=member_id).delete()

    search_query = request.GET.get('search', '')
    members = Member.objects.filter(name__icontains=search_query).order_by('name')

    # ======= Export to Excel =======
    if 'export' in request.GET and request.GET['export'] == 'excel':
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Members')

        # Headers
        worksheet.write(0, 0, 'Name')
        worksheet.write(0, 1, 'Phone')
        worksheet.write(0, 2, 'Work')

        # Data
        for row, member in enumerate(members, start=1):
            worksheet.write(row, 0, member.name)
            worksheet.write(row, 1, member.phone or '')
            worksheet.write(row, 2, member.work or '')

        workbook.close()
        output.seek(0)
        response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=members_list.xlsx'
        return response

    # ======= Export to PDF =======
    if 'export' in request.GET and request.GET['export'] == 'pdf':
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer)
        p.setFont("Helvetica-Bold", 16)
        p.drawString(200, 800, "Members List")

        y = 770
        for i, member in enumerate(members, start=1):
            p.setFont("Helvetica", 12)
            text = f"{i}. {member.name} - {member.phone or ''} - {member.work or ''}"
            p.drawString(50, y, text)
            y -= 20
            if y <= 40:
                p.showPage()
                y = 800
        p.save()
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename='members_list.pdf')

    # ======= Normal View with Pagination =======
    page = request.GET.get('page', 1)
    paginator = Paginator(members, 50)
    members_paginated = paginator.get_page(page)

    return render(request, 'attendance/member_list.html', {
        'members': members_paginated,
        'search_query': search_query,
    })
    
def edit_member(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    if request.method == 'POST':
        member.name = request.POST['name']
        member.work = request.POST.get('work', '')
        member.phone = request.POST.get('phone', '')
        member.save()
    return redirect('member_list')

def export_attendance_excel(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    attendance = Attendance.objects.filter(session=session).select_related('member')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Attendance"

    ws.append(["S.No", "Member Name", "Work", "Phone", "Present?"])

    for i, record in enumerate(attendance, start=1):
        ws.append([
            i,
            record.member.name,
            record.member.work,
            record.member.phone,
            "Yes" if record.is_present else "No"
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"Attendance_{session.name}_{session.date}.xlsx"
    response['Content-Disposition'] = f'attachment; filename={filename}'
    wb.save(response)
    return response

def export_attendance_pdf(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    attendance = Attendance.objects.filter(session=session).select_related('member')

    response = HttpResponse(content_type='application/pdf')
    filename = f"Attendance_{session.name}_{session.date}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    p = canvas.Canvas(response)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, 800, f"Attendance Report - {session.name} ({session.date})")

    y = 760
    p.setFont("Helvetica", 12)
    p.drawString(50, y, "S.No")
    p.drawString(100, y, "Name")
    p.drawString(250, y, "Work")
    p.drawString(400, y, "Phone")
    p.drawString(500, y, "Present")
    y -= 20

    for i, record in enumerate(attendance, start=1):
        if y < 50:
            p.showPage()
            y = 800
        p.drawString(50, y, str(i))
        p.drawString(100, y, record.member.name[:20])
        p.drawString(250, y, record.member.work or "N/A")
        p.drawString(400, y, record.member.phone or "N/A")
        p.drawString(500, y, "Yes" if record.is_present else "No")
        y -= 20

    p.showPage()
    p.save()
    return response

def export_member_pdf(request):
    members = Member.objects.all()

    response = HttpResponse(content_type='application/pdf')
    filename = "Member_List.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # Title
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(width / 2, height - 50, "📜 Member List")
    p.setFont("Helvetica", 12)
    p.drawCentredString(width / 2, height - 70, "All Registered Members")

    y = height - 100

    # Table headers
    p.setFont("Helvetica-Bold", 11)
    p.drawString(40, y, "S.No")
    p.drawString(80, y, "Name")
    p.drawString(200, y, "Work")
    p.drawString(330, y, "Phone")
    y -= 20
    p.setFont("Helvetica", 10)

    # Loop through members
    for i, member in enumerate(members, start=1):
        if y < 60:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica-Bold", 11)
            p.drawString(40, y, "S.No")
            p.drawString(80, y, "Name")
            p.drawString(200, y, "Work")
            p.drawString(330, y, "Phone")
            y -= 20
            p.setFont("Helvetica", 10)

        name = member.name[:25] + ("…" if len(member.name) > 25 else "")
        work = (member.work or "N/A")[:25]
        phone = (member.phone or "N/A")

        p.drawString(40, y, str(i))
        p.drawString(80, y, name)
        p.drawString(200, y, work)
        p.drawString(330, y, phone)
        y -= 20

    p.showPage()
    p.save()

    return response
