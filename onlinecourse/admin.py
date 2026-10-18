from django.contrib import admin
# <HINT> Import any new Models here
from .models import Course, Lesson, Instructor, Learner,Question,Choice,Submission

# <HINT> Register QuestionInline and ChoiceInline classes here

# Display questions inside the Course administration page
class QuestionInline(admin.StackedInline):
    model = Question
    extra = 2


# Display choices inside the Question administration page
class ChoiceInline(admin.StackedInline):
    model = Choice
    extra = 2


# Display lessons inside the Course administration page
class LessonInline(admin.StackedInline):
    model = Lesson
    extra = 5


# Course administration
class CourseAdmin(admin.ModelAdmin):
    inlines = [LessonInline, QuestionInline]
    list_display = ('name', 'pub_date')
    list_filter = ['pub_date']
    search_fields = ['name', 'description']


# Lesson administration
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title']


# Question administration
class QuestionAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]
    list_display = ['text', 'course', 'grade']
    list_filter = ['course']
    search_fields = ['text']


# Submission administration
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['id', 'enrollment']
    list_filter = ['enrollment']


# Register models with Django admin
admin.site.register(Course, CourseAdmin)
admin.site.register(Lesson, LessonAdmin)
admin.site.register(Instructor)
admin.site.register(Learner)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Choice)
admin.site.register(Submission, SubmissionAdmin)