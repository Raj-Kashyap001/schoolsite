from django import template

register = template.Library()


@register.filter
def get_result_for_student(results_list, student_subject_key):
    """Get exam result for a specific student and subject"""
    student_id, subject = student_subject_key.split("_", 1)
    for result in results_list:
        if str(result.student.id) == student_id and result.subject == subject:
            return result
    return None


@register.filter
def key_exists(dictionary, key):
    """Check if key exists in dictionary"""
    return key in dictionary


@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    return dictionary.get(key)
