from django.contrib.sites.shortcuts import get_current_site
from rest_framework import serializers

from pkdb_app.subjects.models import GroupSet, IndividualSet
from pkdb_app.utils import update_or_create_multiple, get_or_val_error
from ..interventions.models import Substance, DataFile, InterventionSet, OutputSet
from ..interventions.serializers import InterventionSetSerializer, OutputSetSerializer
from ..subjects.serializers import GroupSetSerializer, IndividualSetSerializer
from ..users.models import User
from .models import Reference, Author, Study
from ..serializers import WrongKeyValidationSerializer, SidSerializer


class AuthorValidationSerializer(WrongKeyValidationSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = Author
        fields = ('id', 'first_name', 'last_name')

    def create(self, validated_data):
        author, created = Author.objects.update_or_create(**validated_data)
        return author


class ReferenceSerializer(SidSerializer):
    authors = AuthorValidationSerializer(many=True, read_only=False)

    class Meta:
        model = Reference
        fields = ('pmid', 'sid', 'name', 'doi', 'title','abstract', 'journal', 'date', 'authors', 'pdf')

    def create(self, validated_data):
        authors_data = validated_data.pop('authors',[])
        reference = Reference.objects.create(**validated_data)
        update_or_create_multiple(reference,authors_data,"authors")
        reference.save()
        return reference

    def update(self, instance, validated_data):
        authors_data = validated_data.pop('authors',[])
        for name, value in validated_data.items():
            setattr(instance, name, value)
        update_or_create_multiple(instance,authors_data,"authors")
        instance.save()
        return instance


class StudySerializer(SidSerializer):
    reference = serializers.PrimaryKeyRelatedField(queryset=Reference.objects.all(), required=False, allow_null=True)
    groupset = GroupSetSerializer(read_only=False, required=False,allow_null=True)
    curators = serializers.SlugRelatedField(queryset=User.objects.all(), slug_field='username', many=True,required=False,allow_null=True)
    creator = serializers.SlugRelatedField(queryset=User.objects.all(), slug_field='username',required=False,allow_null=True)
    substances = serializers.SlugRelatedField(queryset=Substance.objects.all(), slug_field='name',required=False, many=True,allow_null=True)
    interventionset = InterventionSetSerializer(read_only=False, required=False,allow_null=True)
    individualset = IndividualSetSerializer(read_only=False, required=False, allow_null=True)
    outputset = OutputSetSerializer(read_only=False, required=False, allow_null=True)
    files = serializers.PrimaryKeyRelatedField(queryset=DataFile.objects.all(), required=False, allow_null=True, many=True)

    class Meta:
        model = Study
        fields = ('sid',"pkdb_version","creator",'name',"design",'reference',"curators","substances",
                 "groupset","individualset","interventionset","outputset","files")

    def create(self, validated_data):

        related = self.pop_relations(validated_data)
        creator = validated_data.get("creator")
        if creator:
            validated_data["creator"] = get_or_val_error(User,username=creator)

        instance, _ = Study.objects.update_or_create(sid=validated_data["sid"],
                                                  reference=related["reference"],
                                                  defaults=validated_data,)
        instance = self.create_relations(instance,related)
        instance.save()
        return instance

    def update(self, instance, validated_data):

        related = self.pop_relations(validated_data)
        creator = validated_data.get("creator")

        if creator:
            validated_data["creator"] = get_or_val_error(User, username=creator)

        for name, value in validated_data.items():
                setattr(instance, name, value)
                instance.save()

        instance = self.create_relations(instance,related)
        return instance

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        current_site = f'http://{get_current_site(self.context["request"]).domain}'

        if "files" in rep:
            rep["files"] = [current_site + file.file.url for file in instance.files.all()]
        return rep

    #############################################################################################
    # Helper
    #############################################################################################

    @staticmethod
    def related_sets():
        return {
        "groupset": GroupSet,
        "individualset": IndividualSet,
        "interventionset": InterventionSet,
        "outputset": OutputSet
        }

    def create_relations(self,study,related):
        for name, model in self.related_sets().items():

            if related[name] is not None:
                #if getattr(study, name):
                    #if name == "outputset":
                    #    getattr(study, name).delete()
                instance = model.objects.create(**related[name])
                setattr(study, name, instance)
                study.save()

        for curator_data in related["curators"]:
            curator = get_or_val_error(User, username=curator_data)
            study.curators.add(curator)
            study.save()

        for substance_data in related["substances"]:
            substance = get_or_val_error(Substance, name=substance_data)
            study.substances.add(substance)
            study.save()


        if related["files"]:
            study.files.all().delete()

            for file_pk in related["files"]:
                study.files.add(file_pk)
                study.save()

        return study


    def pop_relations(self ,validated_data):
        related_foreinkeys = self.related_sets().copy()
        related_foreinkeys["reference"] = Reference
        related_many2many = {"substances": Substance, "curators": User, "files": DataFile}
        related_foreinkeys_dict = {name: validated_data.pop(name,None) for name in related_foreinkeys.keys()}
        related_many2many_dict = {name: validated_data.pop(name, []) for name in related_many2many.keys()}
        related = {**related_foreinkeys_dict, **related_many2many_dict}
        return related


