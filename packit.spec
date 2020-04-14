%global pypi_name packitos
%global real_name packit

Name:           %{real_name}
Version:        0.10.0
Release:        1%{?dist}
Summary:        A tool for integrating upstream projects with Fedora operating system

License:        MIT
URL:            https://github.com/packit-service/packit
Source0:        %pypi_source
BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-click-man
BuildRequires:  python3-GitPython
BuildRequires:  python3-gnupg
BuildRequires:  python3-fedmsg
BuildRequires:  python3-jsonschema
BuildRequires:  python3-ogr
BuildRequires:  python3-packaging
BuildRequires:  python3-pyyaml
BuildRequires:  python3-tabulate
BuildRequires:  python3-cccolutils
BuildRequires:  python3-copr
BuildRequires:  python3-koji
BuildRequires:  python3-lazy-object-proxy
BuildRequires:  python3-marshmallow
BuildRequires:  python3-marshmallow-enum
BuildRequires:  rebase-helper
BuildRequires:  python3dist(setuptools)
BuildRequires:  python3dist(setuptools-scm)
BuildRequires:  python3dist(setuptools-scm-git-archive)
# new-sources
Requires:       fedpkg
# bumpspec
Requires:       rpmdevtools
Requires:       python3-%{real_name} = %{version}-%{release}

%description
This project provides tooling and automation to integrate upstream open source
projects into Fedora operating system.

%package -n     python3-%{real_name}
Summary:        %{summary}
# See setup.cfg for details
Requires:       python3-koji
Requires:       python3-bodhi-client
%{?python_provide:%python_provide python3-%{real_name}}

%description -n python3-%{real_name}
Python library for Packit,
check out packit package for the executable.


%prep
%autosetup -n %{pypi_name}-%{version}
# Remove bundled egg-info
rm -rf %{pypi_name}.egg-info

%build
%py3_build

%install
%py3_install
python3 setup.py --command-packages=click_man.commands man_pages --target %{buildroot}%{_mandir}/man1

# FIXME: workaround for setuptools installing it into bash_completion/ instead of bash-completion/
install -d -m 755 %{buildroot}%{_datadir}/bash-completion/completions
mv %{buildroot}%{_datadir}/bash_completion/completions/packit %{buildroot}%{_datadir}/bash-completion/completions/packit

%files
%license LICENSE
%{_bindir}/packit
%{_mandir}/man1/packit*.1*
%dir %{_datadir}/bash-completion/completions
%{_datadir}/bash-completion/completions/%{real_name}

%files -n python3-%{real_name}
%license LICENSE
%doc README.md
%{python3_sitelib}/*

%changelog
* Fri Apr 10 2020 Jiri Popelka <jpopelka@redhat.com> - 0.10.0-1
- new upstream release 0.10.0

* Wed Mar 25 2020 Jiri Popelka <jpopelka@redhat.com> - 0.9.0-1
- new upstream release 0.9.0

* Mon Jan 20 2020 Jiri Popelka <jpopelka@redhat.com> - 0.8.1-1
- new upstream release 0.8.1

* Fri Oct 18 2019 Frantisek Lachman <flachman@redhat.com> - 0.7.1-1
- new upstream release 0.7.1

* Fri Oct 04 2019 Frantisek Lachman <flachman@redhat.com> - 0.7.0-1
- new upstream release 0.7.0

* Thu Sep 12 2019 Jiri Popelka <jpopelka@redhat.com> - 0.6.1-1
- new upstream release: 0.6.1

* Tue Sep 10 2019 Tomas Tomecek <ttomecek@redhat.com> - 0.6.0-1
- new upstream release: 0.6.0

* Fri Aug 23 2019 Tomas Tomecek <ttomecek@redhat.com> - 0.5.1-1
- new upstream release: 0.5.1

* Fri Aug 02 2019 Tomas Tomecek <ttomecek@redhat.com> - 0.5.0-1
- new upstream release: 0.5.0

* Fri Jun 28 2019 Jiri Popelka <jpopelka@redhat.com> - 0.4.2-1
- New upstream release

* Sat May 18 2019 Jiri Popelka <jpopelka@redhat.com> - 0.4.1-1
- Patch release

* Wed May 15 2019 Jiri Popelka <jpopelka@redhat.com> - 0.4.0-1
- New upstream release: 0.4.0
- Build man pages since F30

* Thu Apr 11 2019 Jiri Popelka <jpopelka@redhat.com> - 0.3.0-2
- click-man needs more BuildRequires

* Wed Apr 10 2019 Tomas Tomecek <ttomecek@redhat.com> - 0.3.0-1
- New upstream release: 0.3.0

* Fri Mar 29 2019 Jiri Popelka <jpopelka@redhat.com> - 0.2.0-2
- man pages

* Tue Mar 19 2019 Tomas Tomecek <ttomecek@redhat.com> - 0.2.0-1
- New upstream release 0.2.0

* Thu Mar 14 2019 Frantisek Lachman <flachman@redhat.com> - 0.1.0-1
- New upstream release 0.1.0

* Mon Mar 04 2019 Frantisek Lachman <flachman@redhat.com> - 0.0.1-1
- Initial package.
