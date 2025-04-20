from django.shortcuts import render, redirect, get_object_or_404
from .models import Member, Session, Attendance
from datetime import date, timedelta
from django.core.paginator import Paginator


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
        Attendance.objects.filter(session=session).delete()  # reset
        for member in members:
            is_present = str(member.id) in present_ids
            Attendance.objects.create(session=session, member=member, is_present=is_present)
        return redirect('calendar_view')
    return render(request, 'attendance/mark_attendance.html', {'session': session, 'members': members})

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

    # Pagination and search logic
    search_query = request.GET.get('search', '')
    members = Member.objects.filter(name__icontains=search_query).order_by('name')

    # Pagination setup
    page = request.GET.get('page', 1)
    paginator = Paginator(members, 50)  # Show 5 members per page
    members_paginated = paginator.get_page(page)

    return render(request, 'attendance/member_list.html', {
        'members': members_paginated,
        'search_query': search_query,
    })