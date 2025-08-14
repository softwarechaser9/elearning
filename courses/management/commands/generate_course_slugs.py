from django.core.management.base import BaseCommand
from courses.models import Course


class Command(BaseCommand):
    help = 'Generate slugs for existing courses that don\'t have them'

    def handle(self, *args, **options):
        courses_without_slugs = Course.objects.filter(slug__isnull=True) | Course.objects.filter(slug='')
        
        if not courses_without_slugs.exists():
            self.stdout.write(
                self.style.SUCCESS('All courses already have slugs!')
            )
            return
        
        updated_count = 0
        for course in courses_without_slugs:
            old_slug = course.slug
            course.slug = None  # Clear slug so save() method will generate new one
            course.save()
            updated_count += 1
            
            self.stdout.write(
                f'Updated course "{course.title}": slug "{old_slug}" -> "{course.slug}"'
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated {updated_count} course(s) with new slugs!'
            )
        )
