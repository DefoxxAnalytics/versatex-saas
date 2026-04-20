"""
Forms for procurement data management in Django Admin
"""
from django import forms
from apps.authentication.models import Organization


class CSVUploadForm(forms.Form):
    """
    Form for CSV file upload in Django Admin.
    Supports organization selection for super admins.
    """
    file = forms.FileField(
        label='CSV File',
        help_text='Required columns: supplier, category, amount, date. Optional: description, subcategory, location, fiscal_year, spend_band, payment_method, invoice_number'
    )

    organization = forms.ModelChoiceField(
        queryset=Organization.objects.filter(is_active=True).order_by('name'),
        required=False,
        empty_label='Use my organization (default)',
        help_text='Super admins can select any organization. Leave empty to use your assigned organization.',
        widget=forms.Select(attrs={
            'class': 'organization-select',
            'id': 'id_organization',
            'style': 'background-color: #ffffff !important; color: #000000 !important; -webkit-text-fill-color: #000000 !important;'
        })
    )

    skip_duplicates = forms.BooleanField(
        initial=True,
        required=False,
        label='Skip duplicate records',
        help_text='If checked, duplicate transactions (same supplier, category, amount, date, invoice) will be skipped instead of causing an error.'
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # Refresh queryset to ensure it's up-to-date
        self.fields['organization'].queryset = Organization.objects.filter(is_active=True).order_by('name')

        # Only show organization selector for superusers
        if user and not user.is_superuser:
            self.fields['organization'].widget = forms.HiddenInput()
            self.fields['organization'].required = False

    def clean_file(self):
        """Validate the uploaded file"""
        file = self.cleaned_data.get('file')

        if file:
            # Check file extension
            if not file.name.lower().endswith('.csv'):
                raise forms.ValidationError('File must have .csv extension')

            # Check file size (50MB max)
            if file.size > 50 * 1024 * 1024:
                raise forms.ValidationError('File size must be less than 50MB')

        return file

    def get_organization(self):
        """Get the target organization for the upload"""
        selected_org = self.cleaned_data.get('organization')

        if selected_org:
            return selected_org

        # Fall back to user's organization
        if self.user and hasattr(self.user, 'profile'):
            return self.user.profile.organization

        return None


class OrganizationResetForm(forms.Form):
    """
    Form for organization reset confirmation.
    Requires typing the exact organization name.
    """
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.filter(is_active=True).order_by('name'),
        required=True,
        label='Organization to Reset',
        help_text='Select the organization to completely reset.',
        widget=forms.Select(attrs={
            'class': 'organization-select',
            'id': 'id_organization',
            'style': 'background-color: #ffffff !important; color: #000000 !important; -webkit-text-fill-color: #000000 !important;'
        })
    )

    confirmation = forms.CharField(
        max_length=255,
        required=True,
        label='Confirm Organization Name',
        help_text='Type the exact organization name to confirm.',
        widget=forms.TextInput(attrs={
            'class': 'confirmation-input',
            'placeholder': 'Type organization name exactly',
            'autocomplete': 'off'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        organization = cleaned_data.get('organization')
        confirmation = cleaned_data.get('confirmation', '').strip()

        if organization and confirmation != organization.name:
            raise forms.ValidationError({
                'confirmation': f'Confirmation must match exactly: "{organization.name}"'
            })

        return cleaned_data


class DeleteAllDataForm(forms.Form):
    """
    Form for deleting all transaction data.
    Requires typing "DELETE ALL" to confirm.
    """
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.filter(is_active=True).order_by('name'),
        required=False,  # Only required for superusers
        label='Organization',
        help_text='Select the organization (superusers only).',
        widget=forms.Select(attrs={
            'class': 'organization-select',
            'id': 'id_organization',
            'style': 'background-color: #ffffff !important; color: #000000 !important; -webkit-text-fill-color: #000000 !important;'
        })
    )

    confirmation = forms.CharField(
        max_length=20,
        required=True,
        label='Confirm Deletion',
        help_text='Type "DELETE ALL" to confirm.',
        widget=forms.TextInput(attrs={
            'class': 'confirmation-input',
            'placeholder': 'Type DELETE ALL',
            'autocomplete': 'off'
        })
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # Only show organization selector for superusers
        if user and not user.is_superuser:
            self.fields['organization'].widget = forms.HiddenInput()
            self.fields['organization'].required = False

    def clean_confirmation(self):
        confirmation = self.cleaned_data.get('confirmation', '').strip()
        if confirmation != 'DELETE ALL':
            raise forms.ValidationError('You must type "DELETE ALL" exactly to confirm.')
        return confirmation

    def get_organization(self):
        """Get the target organization for deletion"""
        if self.user and self.user.is_superuser:
            return self.cleaned_data.get('organization')

        # Fall back to user's organization
        if self.user and hasattr(self.user, 'profile'):
            return self.user.profile.organization

        return None
