"""
the managers can be used to overwrite class methods of the models module.
"""
import time
import warnings

import numpy as np
from django.apps import apps
from django.db import models

from pkdb_app.info_nodes.models import MeasurementType
#from pkdb_app.outputs.serializers import OutputSerializer
from ..analysis.pharmacokinetic import f_pk
from ..utils import create_multiple, create_multiple_bulk, create_multiple_bulk_normalized


class OutputSetManager(models.Manager):
    def create(self, *args, **kwargs):
        study = kwargs.pop('study')
        output_exs = kwargs.pop('output_exs', [])
        timecourse_exs = kwargs.pop('timecourse_exs', [])
        descriptions = kwargs.pop('descriptions', [])
        comments = kwargs.pop('comments', [])

        outputset = super().create(*args, **kwargs)

        create_multiple(outputset, descriptions, 'descriptions')
        create_multiple(outputset, comments, 'comments')
        with warnings.catch_warnings(record=True) as ws:

            for output_ex in output_exs:
                intervention_ids = output_ex.pop('interventions', [])
                output_ex_instance = outputset.output_exs.create(**output_ex)
                output_ex_instance.interventions.add(*intervention_ids)
                output_ex_instance.save()
                for timecourse_ex in timecourse_exs:
                    intervention_ids = timecourse_ex.pop('interventions', [])

                    timecourse_ex_instance = outputset.timecourse_exs.create(**timecourse_ex)
                    timecourse_ex_instance.interventions.add(*intervention_ids)
                    timecourse_ex_instance.save()

            outputset.save()
            if len(ws) > 0:
                create_multiple(study, [{"text":w.message} for w in ws], 'warnings')


        return outputset


class OutputExManager(models.Manager):
    def create(self, *args, **kwargs):
        outputs = kwargs.pop('outputs', [])
        interventions = kwargs.pop('interventions', [])
        comments = kwargs.pop('comments', [])
        descriptions = kwargs.pop('descriptions', [])

        output_ex = super().create(*args, **kwargs)

        output_ex.interventions.add(*interventions)
        create_multiple(output_ex, comments, 'comments')
        create_multiple(output_ex, descriptions, 'descriptions')

        outputs_dj = create_multiple(output_ex, outputs, 'outputs')
        Output = apps.get_model('outputs', 'Output')
        outputs_normed = create_multiple_bulk_normalized(outputs_dj, Output)
        for output in outputs_normed:
            output._interventions.add(*output.interventions.all())

        return output_ex


class OutputManager(models.Manager):
    def create(self, *args, **kwargs):
        interventions = kwargs.pop('interventions', [])
        output = super().create(*args, **kwargs)
        output._interventions.add(*interventions)
        return output


class TimecourseExManager(models.Manager):

    @staticmethod
    def _calculate_outputs(timecourse):
        outputs = []
        if timecourse.measurement_type.info_node.name == "concentration" and timecourse.normed:
            variables = timecourse.get_pharmacokinetic_variables()
            c_type = variables.pop("c_type", None)
            _ = variables.pop("bodyweight_type", None)
            pk = f_pk(**variables)

            key_mapping = {"auc": MeasurementType.objects.get(info_node__name="auc_end"),
                           "aucinf": MeasurementType.objects.get(info_node__name="auc_inf"),
                           "cl": MeasurementType.objects.get(info_node__name="clearance"),
                           "cmax": MeasurementType.objects.get(info_node__name="cmax"),
                           "kel": MeasurementType.objects.get(info_node__name="kel"),
                           "thalf": MeasurementType.objects.get(info_node__name="thalf"),
                           "tmax": MeasurementType.objects.get(info_node__name="tmax"),
                           "vd": MeasurementType.objects.get(info_node__name="vd"),
                           }

            for key in ["auc", "aucinf", "cl", "cmax", "kel", "thalf", "vd", "tmax"]:
                pk_unit = pk[f"{key}_unit"]
                if not np.isnan(pk[key]):
                    output_dict = {}
                    output_dict[c_type] = pk[key]
                    output_dict["unit"] = pk_unit
                    output_dict["measurement_type"] = key_mapping[key]
                    output_dict["calculated"] = True
                    output_dict["tissue"] = timecourse.tissue
                    output_dict["substance"] = timecourse.substance
                    output_dict["group"] = timecourse.group
                    output_dict["individual"] = timecourse.individual
                    if output_dict["measurement_type"].info_node.name == "auc_end":
                        output_dict["time"] = max(timecourse.time)
                        output_dict["time_unit"] = timecourse.time_unit
                    outputs.append(output_dict)
        return outputs

    def create(self, *args, **kwargs):

        timecourses = kwargs.pop('timecourses', [])
        interventions = kwargs.pop('interventions', [])
        comments = kwargs.pop('comments', [])
        descriptions = kwargs.pop('descriptions', [])

        timecourse_ex = super().create(*args, **kwargs)
        timecourse_ex.interventions.add(*interventions)
        create_multiple(timecourse_ex, comments, 'comments')
        create_multiple(timecourse_ex, descriptions, 'descriptions')

        timecourses_dj = create_multiple(timecourse_ex, timecourses, 'timecourses')
        Timecourse = type(timecourses_dj[0])

        Output = apps.get_model('outputs', 'Output')

        timecourses_normed = create_multiple_bulk_normalized(timecourses_dj, Timecourse)

        for timecourse in timecourses_normed:
            timecourse._interventions.add(*timecourse.interventions.all())

        # calculate pharmacokinetics data from normalized timecourses
        for timecourse in timecourses_normed:
            outputs = self._calculate_outputs(timecourse)
            #print("*"*100)
            #print(outputs)
            #print("*"*100)
            #OutputSerializer(many=True)
            #serializer = OutputSerializer(data=outputs)
            #serializer.is_valid(raise_exception=True)

            outputs_dj = create_multiple_bulk(timecourse, "timecourse", outputs, Output)
            if outputs_dj:
                outputs_normed = create_multiple_bulk_normalized(outputs_dj, Output)
                for output in outputs_normed:
                    output._interventions.add(*output.interventions.all())

        timecourse_ex.save()
        return timecourse_ex


