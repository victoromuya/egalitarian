from django.db import migrations

SAMPLE_EVENTS = [
    {
        'slug': 'blockchain-bootcamp-july-2026',
        'title': 'Blockchain Developer Bootcamp',
        'date_display': 'July 15-19, 2026',
        'time_display': '9:00 AM - 5:00 PM WAT',
        'location': 'Egalitarian Computers, No. 24 Oyekola Shopping Complex, Jakande Gate, Oke-Afa Isolo, Lagos',
        'price': 500,
        'capacity': 30,
        'event_type': 'Bootcamp',
        'description': 'An intensive five-day bootcamp covering blockchain fundamentals, smart contract development on Ethereum, and building your first decentralized application. Hands-on labs throughout.',
        'topics': 'Blockchain & distributed ledgers, Solidity smart contracts, Ethereum ecosystem, DApp development with Web3.js, Security best practices, Live project build',
    },
    {
        'slug': 'ai-ml-seminar-aug-2026',
        'title': 'AI & Machine Learning Seminar',
        'date_display': 'August 2, 2026',
        'time_display': '10:00 AM - 2:00 PM WAT',
        'location': 'Online (Zoom)',
        'price': 0,
        'capacity': 100,
        'event_type': 'Seminar',
        'description': 'A free half-day seminar exploring the current state of artificial intelligence and machine learning. Ideal for professionals curious about where AI fits in their field.',
        'topics': 'What is AI/ML?, Supervised vs unsupervised learning, Industry applications, Tools & frameworks overview, Career pathways in AI, Q&A with practitioners',
    },
    {
        'slug': 'cybersecurity-workshop-aug-2026',
        'title': 'Cybersecurity Workshop',
        'date_display': 'August 20-21, 2026',
        'time_display': '9:00 AM - 4:00 PM WAT',
        'location': 'Egalitarian Computers, No. 24 Oyekola Shopping Complex, Jakande Gate, Oke-Afa Isolo, Lagos',
        'price': 200,
        'capacity': 25,
        'event_type': 'Workshop',
        'description': 'A practical two-day workshop on cybersecurity fundamentals. Participants will learn to identify common vulnerabilities, understand attacker mindsets, and implement defensive measures.',
        'topics': 'Threat landscape & attack types, Network security fundamentals, Penetration testing basics, Secure coding practices, Incident response, Hands-on CTF challenge',
    },
    {
        'slug': 'cloud-computing-seminar-sept-2026',
        'title': 'Cloud Computing for Professionals',
        'date_display': 'September 10, 2026',
        'time_display': '11:00 AM - 3:00 PM WAT',
        'location': 'Online (Zoom)',
        'price': 0,
        'capacity': 80,
        'event_type': 'Seminar',
        'description': 'Understand the cloud landscape: AWS, Azure, and GCP compared. This seminar targets professionals looking to understand cloud strategy, cost management, and migration basics.',
        'topics': 'Cloud providers compared, IaaS PaaS SaaS explained, Cost management strategies, Migration planning, Security in the cloud, Certification roadmaps',
    },
]


def seed_events(apps, schema_editor):
    Event = apps.get_model('events', 'Event')
    for data in SAMPLE_EVENTS:
        Event.objects.update_or_create(slug=data['slug'], defaults=data)


def unseed_events(apps, schema_editor):
    Event = apps.get_model('events', 'Event')
    Event.objects.filter(slug__in=[d['slug'] for d in SAMPLE_EVENTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_events, unseed_events),
    ]
