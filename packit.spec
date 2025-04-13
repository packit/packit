# Testing dependencies: deepdiff, flexmock are missing on EPEL 9. Cannot use testing environment
%if 0%{?el9}
%bcond_with tests
%else
%bcond_without tests
%endif

Name:           packit
Version:        1.7.0
Release:        1%{?dist}
Summary:        A tool for integrating upstream projects with Fedora operating system

License:        MIT
URL:            https://github.com/packit/packit
Source0:        %{pypi_source packitos}
BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3dist(click-man)
Requires:       python3-packit = %{version}-%{release}

%description
This project provides tooling and automation to integrate upstream open source
projects into Fedora operating system.

%package -n     python3-packit
Summary:        %{summary}
# new-sources
Requires:       fedpkg
Requires:       git-core
# kinit
Requires:       krb5-workstation
# rpmbuild
Requires:       rpm-build
# bumpspec
Requires:       rpmdevtools
# Copying files between repositories
Requires:       rsync

Recommends:       osh-cli

%description -n python3-packit
Python library for Packit,
check out packit package for the executable.


%prep
%autosetup -n packitos-%{version}


%generate_buildrequires
%pyproject_buildrequires %{?with_tests:-x testing}


%build
%pyproject_wheel


%install
%pyproject_install
%pyproject_save_files packit
PYTHONPATH="%{buildroot}%{python3_sitelib}" click-man packit --target %{buildroot}%{_mandir}/man1

install -d -m 755 %{buildroot}%{bash_completions_dir}
cp files/bash-completion/packit %{buildroot}%{bash_completions_dir}/packit


%files
%license LICENSE
%{_bindir}/packit
%{_mandir}/man1/packit*.1*
%{bash_completions_dir}/packit

%files -n python3-packit -f %{pyproject_files}
# Epel9 does not tag the license file in pyproject_files as a license. Manually install it in this case
%if 0%{?el9}
%license LICENSE
%endif
%doc README.md

%changelog
* Sun Apr 13 2025 Packit Team <hello@packit.dev> - 1.7.0-1
- New upstream release 1.7.0

* Fri Apr 04 2025 Packit Team <hello@packit.dev> - 1.6.0-1
- New upstream release 1.6.0

* Mon Mar 31 2025 Packit Team <hello@packit.dev> - 1.5.0-1
- New upstream release 1.5.0

* Fri Mar 28 2025 Packit Team <hello@packit.dev> - 1.4.0-1
- New upstream release 1.4.0

* Fri Mar 14 2025 Packit Team <hello@packit.dev> - 1.3.0-1
- New upstream release 1.3.0

* Sun Feb 23 2025 Packit Team <hello@packit.dev> - 1.2.0-1
- New upstream release 1.2.0

* Fri Feb 14 2025 Packit Team <hello@packit.dev> - 1.1.1-1
- New upstream release 1.1.1

* Sat Feb 01 2025 Packit Team <hello@packit.dev> - 1.1.0-1
- New upstream release 1.1.0

* Sun Jan 26 2025 Packit Team <hello@packit.dev> - 1.0.1-1
- New upstream release 1.0.1

* Fri Jan 17 2025 Packit Team <hello@packit.dev> - 1.0.0-1
- New upstream release 1.0.0

* Fri Dec 13 2024 Packit Team <hello@packit.dev> - 0.106.0-1
- New upstream release 0.106.0

* Fri Dec 06 2024 Packit Team <hello@packit.dev> - 0.105.0-1
- New upstream release 0.105.0

* Mon Nov 25 2024 Packit Team <hello@packit.dev> - 0.104.1-1
- New upstream release 0.104.1

* Fri Nov 15 2024 Packit Team <hello@packit.dev> - 0.104.0-1
- New upstream release 0.104.0

* Sun Nov 10 2024 Packit Team <hello@packit.dev> - 0.103.0-1
- New upstream release 0.103.0

* Mon Oct 21 2024 Packit Team <hello@packit.dev> - 0.102.2-1
- New upstream release 0.102.2

* Fri Oct 11 2024 Packit Team <hello@packit.dev> - 0.102.1-1
- New upstream release 0.102.1

* Fri Oct 04 2024 Packit Team <hello@packit.dev> - 0.102.0-1
- New upstream release 0.102.0

* Tue Sep 17 2024 Packit Team <hello@packit.dev> - 0.101.1-1
- New upstream release 0.101.1

* Fri Sep 06 2024 Packit Team <hello@packit.dev> - 0.101.0-1
- New upstream release 0.101.0

* Tue Aug 20 2024 Packit Team <hello@packit.dev> - 0.100.3-1
- New upstream release 0.100.3

* Wed Aug 14 2024 Packit Team <hello@packit.dev> - 0.100.2-1
- New upstream release 0.100.2

* Thu Aug 01 2024 Packit Team <hello@packit.dev> - 0.100.1-1
- New upstream release 0.100.1

* Mon Jul 29 2024 Packit Team <hello@packit.dev> - 0.100.0-1
- New upstream release 0.100.0

* Fri Jul 12 2024 Packit Team <hello@packit.dev> - 0.99.0-1
- New upstream release 0.99.0

* Thu Jul 04 2024 Packit Team <hello@packit.dev> - 0.98.0-1
- New upstream release 0.98.0

* Fri Jun 21 2024 Packit Team <hello@packit.dev> - 0.97.3-1
- New upstream release 0.97.3

* Thu Jun 06 2024 Packit Team <hello@packit.dev> - 0.97.2-1
- New upstream release 0.97.2

* Fri May 17 2024 Packit Team <hello@packit.dev> - 0.97.1-1
- New upstream release 0.97.1

* Fri May 10 2024 Packit Team <hello@packit.dev> - 0.97.0-1
- New upstream release 0.97.0

* Fri May 03 2024 Packit Team <hello@packit.dev> - 0.96.0-1
- New upstream release 0.96.0

* Sat Apr 20 2024 Packit Team <hello@packit.dev> - 0.95.0-1
- New upstream release 0.95.0

* Mon Apr 08 2024 Packit Team <hello@packit.dev> - 0.94.2-1
- New upstream release 0.94.2

* Mon Mar 25 2024 Packit Team <hello@packit.dev> - 0.94.1-1
- New upstream release 0.94.1

* Sun Mar 17 2024 Packit Team <hello@packit.dev> - 0.94.0-1
- New upstream release 0.94.0

* Mon Feb 26 2024 Packit Team <hello@packit.dev> - 0.93.0-1
- New upstream release 0.93.0

* Sun Feb 18 2024 Packit Team <hello@packit.dev> - 0.92.0-1
- New upstream release 0.92.0

* Wed Feb 07 2024 Packit Team <hello@packit.dev> - 0.91.0-1
- New upstream release 0.91.0

* Fri Jan 26 2024 Packit Team <hello@packit.dev> - 0.90.0-1
- New upstream release 0.90.0

* Fri Jan 19 2024 Packit Team <hello@packit.dev> - 0.89.0-1
- New upstream release 0.89.0

* Sun Jan 07 2024 Packit Team <hello@packit.dev> - 0.88.0-1
- New upstream release 0.88.0

* Thu Nov 30 2023 Packit Team <hello@packit.dev> - 0.87.1-1
- New upstream release 0.87.1

* Fri Nov 24 2023 Packit Team <hello@packit.dev> - 0.87.0-1
- New upstream release 0.87.0

* Mon Nov 20 2023 Packit Team <hello@packit.dev> - 0.86.2-1
- New upstream release 0.86.2

* Mon Nov 20 2023 Packit Team <hello@packit.dev> - 0.86.1-1
- New upstream release 0.86.1

* Thu Nov 16 2023 Packit Team <hello@packit.dev> - 0.86.0-1
- New upstream release 0.86.0

* Mon Oct 30 2023 Packit Team <hello@packit.dev> - 0.85.0-1
- New upstream release 0.85.0

* Mon Oct 16 2023 Packit Team <hello@packit.dev> - 0.84.0-1
- New upstream release 0.84.0

* Fri Oct 06 2023 Packit Team <hello@packit.dev> - 0.83.0-1
- New upstream release 0.83.0

* Fri Sep 29 2023 Packit Team <hello@packit.dev> - 0.82.0-1
- New upstream release 0.82.0

* Thu Sep 21 2023 Packit Team <hello@packit.dev> - 0.81.0-1
- New upstream release 0.81.0

* Fri Sep 08 2023 Packit Team <hello@packit.dev> - 0.80.0-1
- New upstream release 0.80.0

* Mon Aug 21 2023 Packit Team <hello@packit.dev> - 0.79.1-1
- New upstream release 0.79.1

* Fri Aug 11 2023 Packit Team <hello@packit.dev> - 0.79.0-1
- New upstream release 0.79.0

* Fri Aug 04 2023 Packit Team <hello@packit.dev> - 0.78.2-1
- New upstream release 0.78.2
- Confirm License is SPDX compatible.

* Thu Jul 13 2023 Packit Team <hello@packit.dev> - 0.78.1-1
- New upstream release 0.78.1

* Fri Jul 07 2023 Packit Team <hello@packit.dev> - 0.78.0-1
- New upstream release 0.78.0

* Thu Jun 15 2023 Packit Team <hello@packit.dev> - 0.77.0-1
- New upstream release 0.77.0

* Fri May 26 2023 Packit Team <hello@packit.dev> - 0.76.0-1
- New upstream release 0.76.0

* Fri Apr 28 2023 Packit Team <hello@packit.dev> - 0.75.0-1
- New upstream release 0.75.0

* Sun Apr 16 2023 Packit Team <hello@packit.dev> - 0.74.0-1
- New upstream release 0.74.0

* Thu Apr 06 2023 Packit Team <hello@packit.dev> - 0.73.0-1
- New upstream release 0.73.0

* Thu Mar 30 2023 Packit Team <hello@packit.dev> - 0.72.0-1
- New upstream release 0.72.0

* Sat Mar 25 2023 Packit Team <hello@packit.dev> - 0.71.0-1
- New upstream release 0.71.0

* Fri Mar 17 2023 Packit Team <hello@packit.dev> - 0.70.0-1
- New upstream release 0.70.0

* Sun Mar 05 2023 Packit Team <hello@packit.dev> - 0.69.0-1
- New upstream release 0.69.0

* Mon Feb 20 2023 Packit Team <hello@packit.dev> - 0.68.0-1
- New upstream release 0.68.0

* Fri Feb 03 2023 Packit Team <hello@packit.dev> - 0.67.0-1
- New upstream release 0.67.0

* Fri Jan 20 2023 Packit Team <hello@packit.dev> - 0.66.0-1
- New upstream release 0.66.0

* Wed Jan 04 2023 Packit Team <hello@packit.dev> - 0.65.2-1
- New upstream release 0.65.2

* Thu Dec 22 2022 Packit Team <hello@packit.dev> - 0.65.1-1
- New upstream release 0.65.1

* Fri Dec 09 2022 Packit Team <hello@packit.dev> - 0.65.0-1
- New upstream release 0.65.0

* Fri Dec 02 2022 Packit Team <hello@packit.dev> - 0.64.0-1
- New upstream release 0.64.0

* Fri Nov 11 2022 Packit Team <hello@packit.dev> - 0.63.1-1
- New upstream release 0.63.1

* Fri Nov 04 2022 Packit Team <hello@packit.dev> - 0.63.0-1
- New upstream release 0.63.0

* Thu Oct 27 2022 Packit Team <hello@packit.dev> - 0.62.0-1
- New upstream release 0.62.0

* Thu Oct 20 2022 Packit Team <hello@packit.dev> - 0.61.0-1
- New upstream release 0.61.0

* Fri Oct 07 2022 Packit Team <hello@packit.dev> - 0.60.0-1
- New upstream release 0.60.0

* Fri Sep 16 2022 Packit Team <hello@packit.dev> - 0.59.1-1
- New upstream release 0.59.1

* Thu Aug 25 2022 Nikola Forró <nforro@redhat.com> - 0.59.0-1
- New upstream release 0.59.0

* Thu Aug 18 2022 Laura Barcziova <lbarczio@redhat.com> - 0.58.0-1
- New upstream release 0.58.0

* Thu Aug 04 2022 Frantisek Lachman <flachman@redhat.com> - 0.57.0-1
- New upstream release 0.57.0

* Thu Jul 28 2022 Matej Focko <mfocko@redhat.com> - 0.56.0-1
- New upstream release 0.56.0

* Thu Jul 14 2022 František Nečas <fnecas@redhat.com> - 0.55.0-1
- New upstream release 0.55.0

* Wed Jun 29 2022 Tomas Tomecek <ttomecek@redhat.com> - 0.54.0-1
- New upstream release 0.54.0

* Wed Jun 22 2022 Nikola Forró <nforro@redhat.com> - 0.53.0-1
- New upstream release 0.53.0

* Wed Jun 08 2022 Maja Massarini <mmassari@redhat.com> - 0.52.1-1
- New upstream release 0.52.1

* Thu May 26 2022 Laura Barcziova <lbarczio@redhat.com> - 0.52.0-1
- New upstream release 0.52.0

* Thu May 12 2022 Tomas Tomecek <ttomecek@redhat.com> - 0.51.0-1
- New upstream release 0.51.0

* Thu May 05 2022 Matej Focko <mfocko@redhat.com> - 0.50.0-1
- New upstream release 0.50.0

* Tue Apr 12 2022 Jiri Popelka <jpopelka@redhat.com> - 0.49.0-1
- new upstream release 0.49.0

* Wed Mar 30 2022 Maja Massarini <mmassari@redhat.com> - 0.48.0-1
- new upstream release 0.48.0

* Wed Mar 16 2022 Frantisek Lachman <flachman@redhat.com> - 0.47.1-1
- new upstream release 0.47.1

* Tue Mar 8 2022 Jiří Kyjovský <jkyjovsk@redhat.com> - 0.47.0-1
- new upstream release 0.47.0

* Wed Feb 16 2022 Tomas Tomecek <ttomecek@redhat.com> - 0.46.0-1
- new upstream release 0.46.0

* Fri Feb 04 2022 Matej Focko <mfocko@redhat.com> - 0.45.0-1
- new upstream release 0.45.0

* Thu Jan 20 2022 Hunor Csomortáni <csomh@redhat.com> - 0.44.0-1
- new upstream release 0.44.0

* Wed Dec 08 2021 Tomas Tomecek <ttomecek@redhat.com> - 0.43.0-1
- 0.43.0 upstream release

* Wed Nov 24 2021 Laura Barcziova <lbarczio@redhat.com> - 0.42.0-1
- new upstream release 0.42.0

* Thu Nov 11 2021 Hunor Csomortáni <csomh@redhat.com> - 0.41.0-1
- new upstream release 0.41.0

* Tue Oct 26 2021 Frantisek Lachman <flachman@redhat.com> - 0.40.0-1
- new upstream release 0.40.0

* Thu Oct 14 2021 Jiri Kyjovsky <jkyjovsk@redhat.com> - 0.39.0-1
- new upstream release 0.39.0

* Thu Sep 30 2021 Hunor Csomortáni <csomh@redhat.com> - 0.38.0-1
- new upstream release 0.38.0

* Fri Sep 17 2021 Matej Focko <mfocko@redhat.com> - 0.37.0-1
- new upstream release 0.37.0

* Wed Sep 01 2021 Jiri Popelka <jpopelka@redhat.com> - 0.36.0-1
- new upstream release 0.36.0

* Thu Aug 05 2021 Tomas Tomecek <ttomecek@redhat.com> - 0.35.0-1
- new upstream release 0.35.0

* Thu Jul 08 2021 Laura Barcziova <lbarczio@redhat.com> - 0.34.0-1
- new upstream release 0.34.0

* Thu Jun 24 2021 Ben Crocker <bcrocker@redhat.com> - 0.33.1-1
- new upstream release 0.33.1

* Wed Jun 09 2021 Matej Mužila <mmuzila@redhat.com> - 0.32.0-1
- new upstream release 0.32.0

* Thu May 27 2021 Frantisek Lachman <flachman@redhat.com> - 0.31.0-1
- new upstream release 0.31.0

* Fri May 14 2021 Matej Focko <mfocko@redhat.com> - 0.30.1-1
- new upstream release 0.30.1

* Fri May 14 2021 Matej Focko <mfocko@redhat.com> - 0.30.0-1
- new upstream release 0.30.0

* Thu Apr 29 2021 Jiri Popelka <jpopelka@redhat.com> - 0.29.0-1
- new upstream release 0.29.0

* Wed Mar 31 2021 Hunor Csomortáni <csomh@redhat.com> - 0.28.0-1
- new upstream release 0.28.0

* Wed Mar 17 2021 Jiri Popelka <jpopelka@redhat.com> - 0.27.0-1
- new upstream release 0.27.0

* Wed Mar 03 2021 Laura Barcziova <lbarczio@redhat.com> - 0.26.0-1
- new upstream release 0.26.0

* Fri Feb 12 11:11:00 CET 2021 Matej Mužila <mmuzila@redhat.com> - 0.25.0-1
- new upstream release 0.25.0

* Thu Jan 21 10:30:44 CET 2021 Jan Ščotka <jscotka@redhat.com> - 0.24.0-1
- new upstream release 0.24.0

* Thu Jan  7 11:14:24 CET 2021 Frantisek Lachman <flachman@redhat.com> - 0.23.0-1
- new upstream release 0.23.0

* Thu Dec 10 2020 Laura Barcziova <lbarczio@redhat.com> - 0.22.0-1
- new upstream release 0.22.0

* Wed Nov 25 2020 Jiri Popelka <jpopelka@redhat.com> - 0.21.0-1
- new upstream release 0.21.0

* Thu Oct 29 10:42:02 CET 2020 Matej Focko <mfocko@redhat.com> - 0.19.0-1
- new upstream release 0.19.0

* Thu Oct 15 2020 Jiri Popelka <jpopelka@redhat.com> - 0.18.0-1
- new upstream release 0.18.0

* Tue Sep 29 2020 Dominika Hodovska <dhodovsk@redhat.com> - 0.17.0-1
- new upstream release 0.17.0

* Wed Sep 02 2020 Matej Focko <mfocko@redhat.com> - 0.16.0-1
- new upstream release 0.16.0

* Wed Aug 19 2020 Laura Barcziova <lbarczio@redhat.com> - 0.15.0-1
- new upstream release 0.15.0

* Tue Jul 28 2020 Jiri Popelka <jpopelka@redhat.com> - 0.14.0-1
- new upstream release 0.14.0

* Tue Jul 14 2020 Hunor Csomortáni <csomh@redhat.com> - 0.13.1-1
- new upstream release 0.13.1

* Thu Jul 09 2020 Hunor Csomortáni <csomh@redhat.com> - 0.13.0-1
- new upstream release 0.13.0

* Tue Jun 23 2020 Laura Barcziova <lbarczio@redhat.com> - 0.12.0-1
- new upstream release 0.12.0

* Thu Jun 11 2020 Jan Sakalos <sakalosj@gmail.com> - 0.11.1-1
- new upstream release: 0.11.1

* Thu May 28 2020 Tomas Tomecek <ttomecek@redhat.com> - 0.11.0-1
- new upstream release: 0.11.0

* Thu Apr 30 2020 Jan Sakalos <sakalosj@gmail.com> - 0.10.2-1
- new upstream release 0.10.2

* Thu Apr 16 2020 Jiri Popelka <jpopelka@redhat.com> - 0.10.1-1
- new upstream release 0.10.1

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
