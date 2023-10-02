Name:           python-ogr
Version:        0.46.0
Release:        %autorelease
Summary:        One API for multiple git forges

License:        MIT
URL:            https://github.com/packit/ogr
Source0:        %{pypi_source ogr}
BuildArch:      noarch

BuildRequires:  python3-devel

%description
One Git library to Rule!

%package -n     python3-ogr
Summary:        %{summary}


%description -n python3-ogr
One Git library to Rule!


%prep
%autosetup -n ogr-%{version}


%generate_buildrequires
# The -w flag is required for EPEL 9's older hatchling
%pyproject_buildrequires %{?el9:-w}


%build
%pyproject_wheel


%install
%pyproject_install
%pyproject_save_files ogr


%files -n python3-ogr -f %{pyproject_files}
# Epel9 does not tag the license file in pyproject_files as a license. Manually install it in this case
%if 0%{?el9}
%license LICENSE
%endif
%doc README.md


%changelog
%autochangelog
