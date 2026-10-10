"""Course presentation helpers; categories are managed in Django admin."""


def course_group(course):
    return course.category.name
