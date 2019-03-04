%global pypi_name packitos
%global real_name packit

Name:           %{real_name}
Version:        0.0.1
Release:        1%{?dist}
Summary:        A set of tools to integrate upstream open source projects into Fedora operating system

License:        MIT
URL:            https://github.com/packit-service/packit
Source0:        https://files.pythonhosted.org/packages/source/p/%{pypi_name}/%{pypi_name}-%{version}.tar.gz
BuildArch:      noarch

%?python_enable_dependency_generator

%description
This project provides tooling and automation to integrate upstream open source
projects into Fedora operating system.

%package -n     python3-%{real_name}
Summary:        %{summary}
%{?python_provide:%python_provide python3-%{real_name}}

%description -n python3-%{real_name}
This project provides tooling and automation to integrate upstream open source
projects into Fedora operating system.

This package contains the python code,
check out packit package for the executable.


%prep
%autosetup -n %{pypi_name}-%{version}
# Remove bundled egg-info
rm -rf %{pypi_name}.egg-info

%build
%py3_build

%install
%py3_install

%files -n %{real_name}
%{_bindir}/packit

%files -n python3-%{real_name}
%license LICENSE
%doc README.md
%{python3_sitelib}/%{real_name}
%{python3_sitelib}/%{real_name}-%{version}-py?.?.egg-info

%changelog
* Mon Mar 04 2019 Frantisek Lachman <flachman@redhat.com> - 0.1.0-1
- Initial package.
