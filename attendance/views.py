from django.shortcuts import render, redirect, get_object_or_404
from .models import Member, Session, Attendance, Space
from datetime import date, timedelta
from django.core.paginator import Paginator
from django.contrib import messages
import openpyxl
from django.http import HttpResponse, FileResponse
from reportlab.pdfgen import canvas
import io
import xlsxwriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from django.db import IntegrityError


# --------- helper: current space ----------

def get_current_space(request):
    space_id = request.session.get("current_space_id")
    if not space_id:
        return None
    try:
        return Space.objects.get(id=space_id)
    except Space.DoesNotExist:
        return None


# --------- choose / create space ----------

def choose_space(request):
    """
    Shows list of spaces: Main, Second, Third...
    - Click to switch
    - Optionally create a new space
    """
    spaces = Space.objects.all().order_by('id')

    if request.method == "POST":
        # choose existing space
        if "space_id" in request.POST:
            space_id = request.POST.get("space_id")
            request.session["current_space_id"] = int(space_id)
            return redirect('home')

        # create a new space
        new_space_name = request.POST.get("new_space_name", "").strip()
        if new_space_name:
            space = Space.objects.create(name=new_space_name)
            request.session["current_space_id"] = space.id
            return redirect('home')

    current_space = get_current_space(request)
    return render(request, 'attendance/choose_space.html', {
        'spaces': spaces,
        'current_space': current_space,
    })


# --------- existing views, now space-aware ----------

def home(request):
    space = get_current_space(request)
    if not space:
        return redirect('choose_space')

    sessions = Session.objects.filter(space=space).order_by('-date')[:5]
    return render(request, 'attendance/home.html', {
        'sessions': sessions,
        'space': space,
    })


def add_member(request):
    space = get_current_space(request)
    if not space:
        return redirect('choose_space')

    if request.method == "POST":
        name = request.POST.get('name')
        work = request.POST.get('work')
        phone = request.POST.get('phone')

        extra_value = None
        if getattr(space, "has_extra_member_field", False):
            extra_value = request.POST.get('extra_member_value')

        if not name:
            messages.error(request, "Name is required.")
            return redirect('add_member')

        # 🔹 Prevent duplicate phone inside this space
        if phone and Member.objects.filter(space=space, phone=phone).exists():
            messages.error(request, "📞 This phone number is already registered in this space.")
            return redirect('add_member')

        Member.objects.create(
            space=space,
            name=name,
            work=work,
            phone=phone,
            extra_member_value=extra_value,
        )
        messages.success(request, "✅ Member added successfully.")
        return redirect('add_member')

    return render(request, 'attendance/add_member.html', {'space': space})


def add_session(request):
    space = get_current_space(request)
    if not space:
        return redirect('choose_space')

    if request.method == "POST":
        name = request.POST.get('name')
        session_date = request.POST.get('date')
        if name and session_date:
            Session.objects.create(space=space, name=name, date=session_date)
        return redirect('home')
    return render(request, 'attendance/add_session.html', {'space': space})


def mark_attendance(request, session_id):
    space = get_current_space(request)
    if not space:
        return redirect('choose_space')

    session = get_object_or_404(Session, id=session_id, space=space)

    # All members in this space (base queryset)
    members_qs = Member.objects.filter(space=space).order_by('name')

    # Already present members in this session
    present_ids = list(
        Attendance.objects.filter(session=session, is_present=True)
        .values_list('member_id', flat=True)
    )

    if request.method == "POST":
        # IDs that were checked in the form
        present_ids_form = request.POST.getlist('present_members')

        for member in members_qs:
            is_present = str(member.id) in present_ids_form
            attendance, _ = Attendance.objects.get_or_create(session=session, member=member)
            attendance.is_present = is_present
            attendance.save()

        messages.success(request, "✅ Attendance successfully updated!")
        return redirect('mark_attendance', session_id=session_id)

    # ----- GET: apply filter -----
    filter_type = request.GET.get('filter', 'all')

    if filter_type == 'present':
        members = members_qs.filter(id__in=present_ids)
    elif filter_type == 'absent':
        members = members_qs.exclude(id__in=present_ids)
    else:
        filter_type = 'all'
        members = members_qs

    return render(request, 'attendance/mark_attendance.html', {
        'session': session,
        'members': members,
        'present_ids': present_ids,
        'space': space,
        'filter_type': filter_type,
    })



def calendar_view(request):
    space = get_current_space(request)
    if not space:
        return redirect('choose_space')

    days = [date.today() - timedelta(days=i) for i in range(0, 30)]
    sessions = Session.objects.filter(space=space)
    return render(request, 'attendance/calendar.html', {
        'days': days,
        'sessions': sessions,
        'space': space,
    })


def attendance_detail(request, date):
    space = get_current_space(request)
    if not space:
        return redirect('choose_space')

    session = Session.objects.filter(space=space, date=date).first()

    if not session:
        return render(request, 'attendance/attendance_detail.html', {
            'session': None,
            'attendance_list': [],
            'date': date,
            'space': space,
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
    paginator = Paginator(attendance_list, 100)  # Adjust per page count as needed
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'attendance/attendance_detail.html', {
        'session': session,
        'page_obj': page_obj,
        'search_query': search_query,
        'date': date,
        'space': space,
    })


def member_list(request):
    space = get_current_space(request)
    if not space:
        return redirect('choose_space')

    # Handle delete request
    if request.method == 'POST' and 'delete' in request.POST:
        member_id = request.POST['delete']
        Member.objects.filter(id=member_id, space=space).delete()

    search_query = request.GET.get('search', '')
    members = Member.objects.filter(
        space=space,
        name__icontains=search_query
    ).order_by('name')

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
        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
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
    paginator = Paginator(members, 100)
    members_paginated = paginator.get_page(page)

    return render(request, 'attendance/member_list.html', {
        'members': members_paginated,
        'search_query': search_query,
        'space': space,
    })


def edit_member(request, member_id):
    space = get_current_space(request)
    if not space:
        return redirect('choose_space')

    member = get_object_or_404(Member, pk=member_id, space=space)
    if request.method == 'POST':
        member.name = request.POST['name']
        member.work = request.POST.get('work', '')
        member.phone = request.POST.get('phone', '')
        member.save()
    return redirect('member_list')


def export_attendance_excel(request, session_id):
    space = get_current_space(request)
    if not space:
        return redirect('choose_space')

    session = get_object_or_404(Session, id=session_id, space=space)

    # 🔹 Read filter from query string (?filter=present / absent / all)
    filter_type = request.GET.get('filter', 'all')

    attendance_qs = Attendance.objects.filter(session=session).select_related('member')

    if filter_type == 'present':
        attendance_qs = attendance_qs.filter(is_present=True)
    elif filter_type == 'absent':
        attendance_qs = attendance_qs.filter(is_present=False)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Attendance"

    ws.append(["S.No", "Member Name", "Work", "Phone", "Present?"])

    for i, record in enumerate(attendance_qs, start=1):
        ws.append([
            i,
            record.member.name,
            record.member.work,
            record.member.phone,
            "Yes" if record.is_present else "No"
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f"Attendance_{session.name}_{session.date}.xlsx"
    response['Content-Disposition'] = f'attachment; filename={filename}'
    wb.save(response)
    return response

def export_attendance_pdf(request, session_id):
    space = get_current_space(request)
    if not space:
        return redirect('choose_space')

    session = get_object_or_404(Session, id=session_id, space=space)

    # 🔹 Filter type from query string: all / present / absent
    filter_type = request.GET.get('filter', 'all')

    attendance_qs = Attendance.objects.filter(session=session).select_related('member')

    if filter_type == 'present':
        attendance_qs = attendance_qs.filter(is_present=True)
        filter_label = "Present Only"
    elif filter_type == 'absent':
        attendance_qs = attendance_qs.filter(is_present=False)
        filter_label = "Absent Only"
    else:
        filter_type = 'all'
        filter_label = "All Members"

    response = HttpResponse(content_type='application/pdf')
    filename = f"Attendance_{session.name}_{session.date}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    p = canvas.Canvas(response)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, 800, f"Attendance Report - {session.name} ({session.date})")

    # Show which filter is used (All / Present / Absent)
    p.setFont("Helvetica", 11)
    p.drawString(50, 780, f"Filter: {filter_label}")

    # Table header
    y = 750
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "S.No")
    p.drawString(100, y, "Name")
    p.drawString(250, y, "Work")
    p.drawString(400, y, "Phone")
    p.drawString(500, y, "Present")   # 🔹 fixed: 3 args (x, y, text)
    y -= 20

    p.setFont("Helvetica", 11)
    for i, record in enumerate(attendance_qs, start=1):
        if y < 50:
            p.showPage()
            # Re-draw header on new page
            p.setFont("Helvetica-Bold", 12)
            y = 800
            p.drawString(50, y, "S.No")
            p.drawString(100, y, "Name")
            p.drawString(250, y, "Work")
            p.drawString(400, y, "Phone")
            p.drawString(500, y, "Present")
            y -= 20
            p.setFont("Helvetica", 11)

        p.drawString(50, y, str(i))
        p.drawString(100, y, record.member.name[:20])
        p.drawString(250, y, (record.member.work or "N/A")[:20])
        p.drawString(400, y, record.member.phone or "N/A")
        p.drawString(500, y, "Yes" if record.is_present else "No")
        y -= 20

    p.showPage()
    p.save()
    return response



def export_member_pdf(request):
    space = get_current_space(request)
    if not space:
        return redirect('choose_space')

    members = Member.objects.filter(space=space)

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
