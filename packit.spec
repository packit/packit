# Created by pyp2rpm-3.3.2
%global pypi_name we-dont-know-yet
%global real_name packit

Name:           %{real_name}
Version:        0.1.0
Release:        1%{?dist}
Summary:        A set of tools to integrate upstream open source projects into Fedora operating system

License:        MIT
URL:            https://github.com/packit-service/packit
Source0:        TBD
BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  rebase-helper
BuildRequires:  python3dist(setuptools-scm)
BuildRequires:  python3dist(setuptools-scm-git-archive)

%description
This project provides tooling and automation to integrate upstream open source
projects into Fedora operating system.

%package -n     python3-%{real_name}
Summary:        %{summary}
%{?python_provide:%python_provide python3-%{pypi_name}}

Requires:       git-core
Requires:       rebase-helper
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

%files
%{_bindir}/packit
%license LICENSE

%files -n python3-%{real_name}
%license LICENSE
%doc README.md
%{python3_sitelib}/%{real_name}
%{python3_sitelib}/%{real_name}-%{version}-py?.?.egg-info

%changelog
* Wed Feb 27 2019 Tomas Tomecek <ttomecek@redhat.com> - 0.1-1
- Initial package.
