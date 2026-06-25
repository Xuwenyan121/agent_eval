"""Add conv_id_strategy field to EvaluationTask."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("evaluation", "0003_add_judge_model"),
    ]

    operations = [
        migrations.AddField(
            model_name="evaluationtask",
            name="conv_id_strategy",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("dataset", "Use dataset convId (multi-turn for same convId)"),
                    ("isolated", "Unique convId per sample (all single-turn)"),
                    ("shared", "All samples share one convId (one session)"),
                ],
                default="dataset",
                help_text="How convId is assigned: dataset-driven, per-sample isolated, or shared session",
            ),
        ),
    ]
