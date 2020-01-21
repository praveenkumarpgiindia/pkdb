"""
Model for the InfoNodes.

"""
from pint import UndefinedUnitError
from numbers import Number
from django.db import models
from django.utils.translation import gettext_lazy as _


from pkdb_app.info_nodes.managers import InfoNodeManager
from pkdb_app.info_nodes.units import ureg
from pkdb_app.behaviours import Sidable
from pkdb_app.users.models import User
from pkdb_app.utils import CHAR_MAX_LENGTH, _validate_requried_key


class Annotation(models.Model):

    """ Annotation Model
    """
    term = models.CharField(max_length=CHAR_MAX_LENGTH)
    relation = models.CharField(max_length=CHAR_MAX_LENGTH, )
    collection = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    description = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    label = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)


class InfoNode(models.Model, Sidable):


    # todo:proably remove
    class NoteTypes(models.TextChoices):
        """ Note Types. """

        Substance = 'substance', _('substance')
        MeasurementType = 'measurement_type', _('measurement_type')
        Route = 'route', _('route')
        Form = 'form', _('form')
        Application = 'application', _('application')
        Tissue = 'tissue', _('tissue')
        Choice = 'choice', _('choice')

    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    url_slug = models.CharField(max_length=CHAR_MAX_LENGTH, unique=True)
    description = models.TextField(blank=True, null=True)
    creator = models.ForeignKey(User, related_name="info_nodes", on_delete=models.CASCADE)
    annotations = models.ManyToManyField(Annotation)
    parents = models.ManyToManyField("InfoNode", related_name="children")
    node_type = models.CharField(choices=NoteTypes.choices, max_length=20)

    def annotations_strings(self):
        return [f"relation <{annotation.relation}>:, {annotation.term}" for annotation in self.annotations.all()]


    def _asdict(self): #todo: should be done via serializer class ?
        return {
            "name": self.name,
            "description": self.description,
            "annotations": self.annotations_strings(),
            "url_slug": self.url_slug,
            "creator": self.creator.username,
        }


class Synonym(models.Model):
    """Synonyms Model"""
    name = models.CharField(max_length=CHAR_MAX_LENGTH, unique=True)
    info_node = models.ForeignKey(InfoNode, on_delete=models.CASCADE, related_name="synonyms", null=True)


class AbstractInfoNode(models.Model):

    objects = InfoNodeManager()

    class Meta:
        abstract = True


class Choice(AbstractInfoNode):
    info_node = models.OneToOneField(
        InfoNode, related_name="choice", on_delete=models.SET_NULL, null=True)


class Tissue(AbstractInfoNode):
    """ Tissue Model """
    info_node = models.OneToOneField(
        InfoNode, related_name="tissue", on_delete=models.SET_NULL, null=True
    )


class Route(AbstractInfoNode):
    """ Route Model """

    info_node = models.OneToOneField(
        InfoNode, related_name="route", on_delete=models.SET_NULL, null=True
    )


class Application(AbstractInfoNode):
    """ Application Model """
    info_node = models.OneToOneField(
        InfoNode, related_name="application", on_delete=models.SET_NULL, null=True
    )


class Form(AbstractInfoNode):
    """ Form Model """
    info_node = models.OneToOneField(
        InfoNode, related_name="form", on_delete=models.SET_NULL, null=True
    )


class Unit(models.Model):
    """Units Model"""
    name = models.CharField(max_length=CHAR_MAX_LENGTH)

    @property
    def p_unit(self):
        return ureg(self.name).u


class MeasurementType(AbstractInfoNode):
    """ MeasurementType Model """
    info_node = models.OneToOneField(
        InfoNode, related_name="measurement_type", on_delete=models.SET_NULL, null=True
    )

    NO_UNIT = 'NO_UNIT' #todo: remove NO_UNIT and add extra keyword or add an extra measurement_type with optional no units.
    TIME_REQUIRED_MEASUREMENT_TYPES = ["cumulative amount", "cumulative metabolic ratio", "recovery", "auc_end"]  #todo: remove and add extra keyword.
    CAN_NEGATIVE = [] # todo remove
    ADDITIVE = [] # todo remove

    class DTypes(models.TextChoices):
        """ Data Types. """
        Abstract = 'abstract', _('abstract')
        Boolean = 'boolean', _('boolean')
        Numeric = 'numeric', _('numeric')
        Categorical = 'categorical', _('categorical')
        NumericCategorical = 'numeric_categorical', _('numeric_categorical')

    units = models.ManyToManyField(Unit, related_name="measurement_types")
    dtype = models.CharField(choices=DTypes.choices, max_length=20)


    @property
    def choices(self):
     assert NotImplementedError
     return None

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    @property
    def n_p_units(self):
        """
        :return: list of normalized units in the data format of pint
        """
        return [unit.p_unit for unit in self.units.all()]

    @property
    def n_units(self):
        """
        :return: list of normalized units as strings
        """
        return self.units.values_list("name", flat=True)

    @property
    def valid_dimensions(self):
        return [unit.dimensionality for unit in self.n_p_units]

    @property
    def valid_dimensions_str(self):
        return [str(unit.dimensionality) for unit in self.n_p_units]

    @property
    def dimension_to_n_unit(self):
        return {str(n_unit_p.dimensionality): n_unit_p for n_unit_p in self.n_p_units}

    @staticmethod
    def p_unit(unit):
        try:
            return ureg(unit)
        except (UndefinedUnitError, AttributeError):
            if unit == "%":
                raise ValueError(f"unit: [{unit}] has to written as 'percent'")

            raise ValueError(f"unit [{unit}] is not defined in unit registry or not allowed.")

    def is_valid_unit(self, unit):

        if len(self.n_units) != 0:
            if unit:
                return any([self.p_unit(unit).check(dim) for dim in self.valid_dimensions])
            else:
                # unit_not_required2 = self.dtype == NUMERIC_CATEGORIAL_TYPE
                # return unit_not_required2
                unit_not_required2 = self.NO_UNIT in self.n_units
                return unit_not_required2

        else:
            if unit:
                return False
            else:
                return True

    def validate_unit(self, unit):
        if not self.is_valid_unit(unit):
            msg = f"For measurement type `{self.name}` the unit [{unit}] with dimension {self.unit_dimension(unit)} " \
                  f"is not allowed."
            raise ValueError(
                {"unit": msg, "Only units with the following dimensions are allowed:": self.valid_dimensions_str,
                 "Units are allowed which can be converted to the following normalized units:": self.n_units})

    def is_valid_time_unit(self, time_unit):
        return self.p_unit(time_unit).dimensionality == '[time]'

    def validate_time_unit(self, unit):
        if not self.is_valid_time_unit(unit):
            msg = f"[{unit}] with dimension [{self.unit_dimension(unit)}] is not allowed for the time units. "
            raise ValueError({"time_unit": msg})

    def norm_unit(self, unit):
        try:
            return self.dimension_to_n_unit[str(self.unit_dimension(unit))]
        except KeyError:
            raise ValueError(
                f"Dimension [{self.unit_dimension(unit)}] is not allowed for measurement type [{self.name}]."
                f" Dimension was calculated from unit :[{unit}]")

    def unit_dimension(self, unit):
        return self.p_unit(unit).dimensionality

    def is_norm_unit(self, unit):
        return ureg(unit) in self.n_p_units

    def normalize(self, magnitude, unit):
        this_unit_p = self.p_unit(unit)
        this_norm_unit_p = self.norm_unit(unit)
        result = (magnitude * this_unit_p).to(this_norm_unit_p)
        return result

    def is_valid_choice(self, choice):
        return choice in self.choices.values_list("name", flat=True)

    def choices_list(self):
        return self.choices.values_list("name", flat=True)

    def _asdict(self):
        # todo: should be done via serializer class ?
        return {
            **self.info_node._asdict(),
            "dtype": self.dtype,
            "choices": self.choices_list(),
            "units": self.n_units,
            "valid unit dimensions": self.valid_dimensions
        }
    @property
    def time_required(self):
        if self.name in self.TIME_REQUIRED_MEASUREMENT_TYPES:
            return True
        else:
            False



    def validate_choice(self, choice):
        if choice:
            if self.dtype in [self.DTypes.CATEGORIAL_TYPE, self.DTypes.BOOLEAN_TYPE, self.DTypes.NUMERIC_CATEGORIAL_TYPE]:
                if not self.is_valid_choice(choice):
                    msg = f"The choice `{choice}` is not a valid choice for measurement type `{self.name}`. " \
                          f"Allowed choices are: `{list(self.choices_list())}`."
                    raise ValueError({"choice": msg})
            else:
                msg = f"The field `choice` is not allowed for measurement type `{self.name}`. " \
                      f"For numerical values the fields `value`, `mean` or `median` are used. " \
                      f"For encoding substances use the `substance` field."
                raise ValueError({"choice": msg})
        elif self.choices.exists():
            msg = f"{choice}. A choice is required for `{self.name}`." \
                  f" Allowed choices are: `{list(self.choices_list())}`."
            raise ValueError({"choice": msg})

    @property
    def numeric_fields(self):
        return ["value", "mean", "median", "min", "max", "sd", "se", "cv"]

    @property
    def can_be_negative(self):
        return self.name in self.CAN_NEGATIVE

    def validate_numeric(self, data):
        if self.dtype in [self.DTypes.NUMERIC_CATEGORIAL_TYPE, self.DTypes.NUMERIC_TYPE]:
            for field in self.numeric_fields:
                value = data.get(field)
                if not self.can_be_negative:

                    if isinstance(value, Number):
                        rule = value < 0
                    # for timecourses

                    elif isinstance(value, list):
                        rule = any(v < 0 for v in value)

                    else:
                        rule = False

                    if rule:
                        raise ValueError(
                            {field: f"Numeric values need to be positive (>=0) "
                                    f"for all measurement types except "
                                    f"<{self.CAN_NEGATIVE}>.", "detail": data})

    def validate_complete(self, data):
        # check unit

        self.validate_unit(data.get("unit", None))
        self.validate_numeric(data)

        choice = data.get("choice", None)
        self.validate_choice(choice)

        time_unit = data.get("time_unit", None)
        if time_unit:
            self.validate_time_unit(time_unit)

        if self.time_required:
            details = f"for measurement type `{self.name}`"
            _validate_requried_key(data, "time", details=details)
            _validate_requried_key(data, "time_unit", details=details)

    @property
    def creator_username(self):
        """
        :return: list of normalized units in the data format of pint
        """
        return self.creator.username


class Substance(AbstractInfoNode):
    """ Substances.

    There could be three main classes of `substances`:
    1. Substance with a chebi identifier
    - this is a basic substance and can have a mass (or not)
    2. Substance with no chebi identifier
    - this is a basic substance and can have a mass (or not)
    3. Derived substance (with no chebi identifier)
    - this is a combination of basic substances (from class 1 or 2).
    - this has no mass
    - if all partial substances have mass this could be used for unit transformations ?!

    Has to be extended via ontology (Ontologable)
    """
    # this cannot be null (for class 1 & 2), must be null for class 3
    chebi = models.CharField(null=True, max_length=CHAR_MAX_LENGTH, unique=True)
    mass = models.FloatField(null=True)
    charge = models.FloatField(null=True)
    formula = models.CharField(null=True, max_length=CHAR_MAX_LENGTH)  # chemical formula



    def __str__(self):
        return self.name

    @property
    def derived(self):
        # validation rule: check that all labels are in derived and not more(split on `+/()`)
        return self.parents.exists()

    @property
    def outputs_normed(self):
        return self.output_set.filter(normed=True)

    @property
    def outputs_calculated(self):
        return self.output_set.filter(normed=True, calculated=True)

    @property
    def timecourses_normed(self):
        return self.timecourse_set.filter(normed=True)

    @property
    def interventions_normed(self):
        return self.intervention_set.filter(normed=True)

    @property
    def creator_username(self):
        return self.creator.username
