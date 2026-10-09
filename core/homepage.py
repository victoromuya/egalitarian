"""Presentation content for the reference-inspired homepage."""

import re

COURSE_GROUPS = ['Data', 'Web', 'Blockchain', 'Desktop Publishing']


def course_group(course):
    subject = f'{course.title} {course.slug} {course.category}'.lower().replace('-', ' ')
    if re.search(r'\b(blockchain|solidity|web3|smart contracts?)\b', subject):
        return 'Blockchain'
    if re.search(r'\b(desktop publishing|indesign|dtp)\b', subject):
        return 'Desktop Publishing'
    if re.search(r'\b(web|html|css|django|react|frontend|front end|full stack)\b', subject):
        return 'Web'
    if re.search(r'\b(data|analytics|computer vision|machine learning|artificial intelligence)\b', subject):
        return 'Data'
    return ''

COURSE_ART = {'Programming': 'programming', 'Web Design': 'web-design', 'Business': 'business', 'Language': 'language', 'Film & Video': 'film-video', 'Photography': 'photography'}
