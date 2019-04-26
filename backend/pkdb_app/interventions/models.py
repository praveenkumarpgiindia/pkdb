"""
Describe Interventions and Output (i.e. define the characteristics of the
group or individual).
"""
from django.db import models
from pkdb_app.categorials.models import InterventionType
from pkdb_app.substances.models import Substance

from ..utils import CHAR_MAX_LENGTH, create_choices
from ..subjects.models import DataFile

from ..interventions.managers import InterventionSetManager,InterventionExManager
from ..behaviours import Externable, ValueableNotBlank, ValueableMapNotBlank, Normalizable


# -------------------------------------------------
# Intervention
# -------------------------------------------------


#
# Choices for intervention routes, application and form.
#

INTERVENTION_ROUTE = [
    "iv",  # intravenous
    "intramuscular",
    "oral",
    "rectal",
]
INTERVENTION_APPLICATION = [
    "constant infusion",
    "multiple dose",
    "single dose",
    "variable infusion",
]
INTERVENTION_FORM = [
    "capsule",
    "tablet",
    "solution",
    "no info",
]
INTERVENTION_APPLICATION_CHOICES = create_choices(INTERVENTION_APPLICATION)
INTERVENTION_ROUTE_CHOICES = create_choices(INTERVENTION_ROUTE)
INTERVENTION_FORM_CHOICES = create_choices(INTERVENTION_FORM)


class InterventionSet(models.Model):
    objects = InterventionSetManager()

    @property
    def interventions(self):
        """ all interventions """
        interventions = Intervention.objects.filter(ex__in=self.intervention_exs.all())
        return interventions

    @property
    def interventions_normed(self):
        """ all interventions """
        interventions = self.interventions.filter(normed=True)
        return interventions

    @property
    def count(self):
        if self.interventions:
            return self.interventions.count()
        else:
            return 0


class AbstractIntervention(models.Model):


    choice = models.CharField(max_length=CHAR_MAX_LENGTH * 3, null=True)
    form = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, choices=INTERVENTION_FORM_CHOICES)
    application = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, choices=INTERVENTION_APPLICATION_CHOICES)
    time = models.FloatField(null=True)
    time_unit = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    substance = models.ForeignKey(Substance, null=True, on_delete=models.SET_NULL)
    route = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, choices=INTERVENTION_ROUTE_CHOICES)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class AbstractInterventionMap(models.Model):
    choice_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    form_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    application_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    time_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    time_unit_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    substance_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    route_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)

    class Meta:
        abstract = True


class InterventionEx(
    Externable,
    ValueableNotBlank,
    ValueableMapNotBlank,
    AbstractIntervention,
    AbstractInterventionMap,
):
    """ Intervention (external curated layer)."""

    source = models.ForeignKey(
        DataFile,
        related_name="s_intervention_exs",
        null=True,
        on_delete=models.SET_NULL,
    )
    figure = models.ForeignKey(
        DataFile,
        related_name="f_intervention_exs",
        null=True,
        on_delete=models.SET_NULL,
    )

    interventionset = models.ForeignKey(
        InterventionSet, related_name="intervention_exs", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    name_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    category = models.CharField(max_length=CHAR_MAX_LENGTH)
    objects = InterventionExManager()

    class Meta:
        unique_together = ("interventionset", "name", "name_map", "source")


class Intervention(Normalizable, ValueableNotBlank, AbstractIntervention):
    """ A concrete step/thing which is done to the group.

         In case of dosing/medication the actual dosing is stored in the Valueable.
         In case of a step without dosing, e.g., lifestyle intervention only the category is used.
      """
    category = models.ForeignKey(InterventionType,on_delete=models.CASCADE)
    ex = models.ForeignKey(
        InterventionEx,
        related_name="interventions",
        null=True,
        on_delete=models.CASCADE,
    )

    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    raw = models.ForeignKey("Intervention", related_name="norm", on_delete=models.CASCADE, null=True)
    normed = models.BooleanField(default=False)
    substance = models.ForeignKey(Substance, related_name="interventions", null=True, on_delete=models.PROTECT)

    @property
    def study(self):
        return self.ex.interventionset.study.name

    @property
    def category_key(self):
        return self.category.key
