
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evaluation', '0005_add_expected_meta'),
    ]

    operations = [
        migrations.AddField(
            model_name='agentendpoint',
            name='verify_ssl',
            field=models.BooleanField(default=True, help_text='Verify SSL certificate (disable for self-signed certs)'),
        ),
    ]
