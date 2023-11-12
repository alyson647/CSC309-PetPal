from django.utils import timezone
from rest_framework.generics import UpdateAPIView, ListAPIView, RetrieveAPIView, get_object_or_404, \
    ListCreateAPIView, RetrieveUpdateDestroyAPIView, RetrieveUpdateAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission, IsAuthenticated
from accounts.models import ShelterUser, PetUser, CustomUser
from pets.models import Applications, Pet
from pets.serializers.application_serializers import ApplicationSerializer, ApplicationUpdateSerializer


class ApplicationPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        shelter = obj.pet_listing.shelter
        applicant = obj.applicant
        if request.user.username == shelter.username or request.user.username == applicant.username:
            return True
        return False


class ApplicationCreateListView(ListCreateAPIView):
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated, ApplicationPermission]
    pagination_class = PageNumberPagination

    def perform_create(self, serializer):
        pet_listing = serializer.validated_data['pet_listing']
        if pet_listing.status == 'AV':
            pet_seeker = PetUser.objects.filter(username=self.request.user.username)[0]
            serializer.save(applicant=pet_seeker)

    def get_queryset(self):
        if isinstance(self.request.user, ShelterUser):
            shelter = ShelterUser.objects.filter(username=self.request.user.username)[0]
            pet_listing = Pet.objects.filter(shelter=shelter)
            return (Applications.objects.filter(pet_listing=pet_listing).order_by('creation_time')
                    .order_by('last_modified'))
        else:
            return (Applications.objects.filter(applicant=self.request.user).order_by('creation_time')
                    .order_by('last_modified'))


class ApplicationGetUpdateView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, ApplicationPermission]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ApplicationUpdateSerializer
        return ApplicationSerializer

    def perform_update(self, serializer):
        shelter = ShelterUser.objects.filter(username=self.request.user.username)
        current_shelter = serializer.instance.pet_listing.shelter
        if current_shelter.username == shelter.username:
            if serializer.instance.status == 'pending' and serializer.validated_data['status'] in ['accepted',
                                                                                                   'denied']:
                serializer.save(status=serializer.validated_data['status'], last_modified=timezone.now())
        else:
            if (serializer.instance.status in ['pending', 'accepted'] and
                    serializer.validated_data.get('status') == 'withdrawn'):
                serializer.save(status=serializer.validated_data['status'], last_modified=timezone.now())

    def get_object(self):
        return get_object_or_404(Applications, id=self.kwargs['pk'])
