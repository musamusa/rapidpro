# Generated by Django 4.0.3 on 2022-03-10 17:56

from django.db import migrations

from . import InstallSQL


class Migration(migrations.Migration):

    dependencies = [("msgs", "0169_squashed"), ("notifications", "0008_squashed")]

    operations = [InstallSQL("0004_functions"), InstallSQL("0004_indexes"), InstallSQL("0004_triggers")]
