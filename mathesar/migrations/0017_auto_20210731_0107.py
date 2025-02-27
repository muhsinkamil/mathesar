# Generated by Django 3.1.7 on 2021-07-31 01:07

from django.db import migrations, models

from mathesar.models.base import DataFile


class Migration(migrations.Migration):

    dependencies = [
        ('mathesar', '0016_auto_20210728_2156'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datafile',
            name='created_from',
            field=models.CharField(choices=DataFile.created_from_choices.choices,
                                   max_length=128)
        ),
    ]
