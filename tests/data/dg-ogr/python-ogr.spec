# created by pyp2rpm-3.3.2
%global pypi_name ogr

%{?python_enable_dependency_generator}

Name:           python-%{pypi_name}
Version:        0.7.0
Release:        1%{?dist}
Summary:        One API for multiple git forges

License:        MIT
URL:            https://github.com/packit-service/ogr
Source0:        https://files.pythonhosted.org/packages/source/o/%{pypi_name}/%{pypi_name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  python3dist(setuptools)
BuildRequires:  python3dist(setuptools-scm)
BuildRequires:  python3dist(setuptools-scm-git-archive)

%description
One Git library to Rule!

%package -n     python3-%{pypi_name}
Summary:        %{summary}
%{?python_provide:%python_provide python3-%{pypi_name}}

%description -n python3-%{pypi_name}
One Git library to Rule!


%prep
%autosetup -n %{pypi_name}-%{version}
# Remove bundled egg-info
rm -rf %{pypi_name}.egg-info


%build
%py3_build


%install
%py3_install


%files -n python3-%{pypi_name}
%license LICENSE
%doc README.md
%{python3_sitelib}/%{pypi_name}
%{python3_sitelib}/%{pypi_name}-%{version}-py?.?.egg-info


%changelog
* Thu Sep 12 2019 Frantisek Lachman <flachman@redhat.com> - 0.7.0-1
- new upstream release: 0.7.0

* Mon Aug 19 2019 Miro Hrončok <mhroncok@redhat.com> - 0.6.0-2
- Rebuilt for Python 3.8

* Thu Aug 01 2019 Packit Service - 0.6.0-1
- new upstream release: 0.6.0

* Fri Jul 26 2019 Fedora Release Engineering <releng@fedoraproject.org> - 0.5.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_31_Mass_Rebuild

* Fri Jun 28 2019 Frantisek Lachman <flachman@redhat.com> - 0.5.0-1
- New upstream release: 0.5.0

* Tue Jun 11 2019 Jiri Popelka <jpopelka@redhat.com> - 0.4.0-1
- New upstream release: 0.4.0

* Tue May 14 2019 Jiri Popelka <jpopelka@redhat.com> - 0.3.1-1
- patch release: 0.3.1

* Mon May 13 2019 Jiri Popelka <jpopelka@redhat.com> - 0.3.0-1
- New upstream release: 0.3.0

* Wed Mar 27 2019 Tomas Tomecek <ttomecek@redhat.com> - 0.2.0-1
- New upstream release: 0.2.0

* Mon Mar 18 2019 Tomas Tomecek <ttomecek@redhat.com> - 0.1.0-1
- New upstream release: 0.1.0

* Thu Feb 28 2019 Frantisek Lachman <flachman@redhat.com> - 0.0.3-1
- New upstream release 0.0.3

* Tue Feb 26 2019 Tomas Tomecek <ttomecek@redhat.com> - 0.0.2-1
- Initial package.
