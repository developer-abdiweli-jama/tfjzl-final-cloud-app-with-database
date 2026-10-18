from django.shortcuts import render
from django.http import HttpResponseRedirect
# <HINT> Import any new Models here
from .models import Course, Enrollment, Question, Choice, Submission
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(
            request,
            'onlinecourse/user_registration_bootstrap.html',
            context
        )
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except User.DoesNotExist:
            logger.error("New user")

        if not user_exist:
            user = User.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
                password=password
            )
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(
                request,
                'onlinecourse/user_registration_bootstrap.html',
                context
            )


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(
                request,
                'onlinecourse/user_login_bootstrap.html',
                context
            )
    else:
        return render(
            request,
            'onlinecourse/user_login_bootstrap.html',
            context
        )


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(
            user=user,
            course=course
        ).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(
            user=user,
            course=course,
            mode='honor'
        )
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(
        reverse(
            viewname='onlinecourse:course_details',
            args=(course.id,)
        )
    )


# <HINT> Create a submit view to create an exam submission record for a course enrollment,
# you may implement it based on following logic:
#         # Get user and course object, then get the associated enrollment object created when the user enrolled the course
#         # Create a submission object referring to the enrollment
#         # Collect the selected choices from exam form
#         # Add each selected choice object to the submission object
#         # Redirect to show_exam_result with the submission id


# An example method to collect the selected choices from the exam form from the request object
def extract_answers(request):
    submitted_answers = []

    for key in request.POST:
        if key.startswith('choice_'):
            for value in request.POST.getlist(key):
                try:
                    submitted_answers.append(int(value))
                except (ValueError, TypeError):
                    continue

    return submitted_answers


@login_required
@require_POST
def submit(request, course_id):
    # Get user and course object
    course = get_object_or_404(Course, pk=course_id)

    # Get the enrollment associated with the current user
    enrollment = get_object_or_404(
        Enrollment,
        user=request.user,
        course=course
    )

    # Create a submission object
    submission = Submission.objects.create(enrollment=enrollment)

    # Collect the selected choices from the exam form
    selected_ids = extract_answers(request)

    # Only accept choices belonging to questions in this course
    valid_choices = Choice.objects.filter(
        question__course=course,
        id__in=selected_ids
    )

    # Add selected choices to the submission
    submission.choices.set(valid_choices)

    # Redirect to the exam results
    return redirect(
        'onlinecourse:show_exam_result',
        course_id=course.id,
        submission_id=submission.id
    )


# <HINT> Create an exam result view to check if learner passed exam and show their question results and result for each question,
# you may implement it based on following logic:
#        # Get course and submission based on their ids
#        # Get the selected choice ids from the submission record
#        # For each selected choice, check if it is a correct answer or not
#        # Calculate the total score

@login_required
def show_exam_result(request, course_id, submission_id):
    # Get the course
    course = get_object_or_404(Course, pk=course_id)

    # Get the submission belonging to this user and course
    submission = get_object_or_404(
        Submission,
        pk=submission_id,
        enrollment__course=course,
        enrollment__user=request.user
    )

    # Get selected choice IDs
    selected_ids = set(
        submission.choices.values_list('id', flat=True)
    )

    question_results = []
    total_grade = 0
    earned_grade = 0

    # Evaluate each question in the course
    questions = course.question_set.prefetch_related('choice_set').all()

    for question in questions:
        choices = list(question.choice_set.all())

        correct_ids = {
            choice.id
            for choice in choices
            if choice.is_correct
        }

        selected_for_question = {
            choice.id
            for choice in choices
            if choice.id in selected_ids
        }

        # All correct choices must be selected, with no incorrect choices
        is_correct = (
            bool(correct_ids)
            and selected_for_question == correct_ids
        )

        total_grade += question.grade
        question_grade = question.grade if is_correct else 0
        earned_grade += question_grade

        question_results.append({
            'question': question,
            'choices': choices,
            'selected_ids': selected_for_question,
            'correct_ids': correct_ids,
            'is_correct': is_correct,
            'grade': question_grade,
        })

    # Calculate percentage for the existing results template
    percentage = (
        (earned_grade / total_grade) * 100
        if total_grade > 0
        else 0
    )

    # The original results template uses grade > 80
    passed = percentage > 80

    context = {
        'course': course,
        'submission': submission,
        'question_results': question_results,
        'grade': percentage,
        'earned_grade': earned_grade,
        'total_grade': total_grade,
        'passed': passed,
    }

    return render(
        request,
        'onlinecourse/exam_result_bootstrap.html',
        context
    )