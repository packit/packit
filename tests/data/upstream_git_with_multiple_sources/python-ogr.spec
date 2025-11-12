Name:           python-ogr
Version:        0.57.0
Release:        1%{?dist}
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
%pyproject_buildrequires


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
* Fri Oct 31 2025 Packit Team <hello@packit.dev> - 0.57.0-1
- New upstream release 0.57.0

* Fri Oct 03 2025 Packit Team <hello@packit.dev> - 0.56.1-1
- New upstream release 0.56.1

* Wed Aug 20 2025 Packit Team <hello@packit.dev> - 0.56.0-1
- New upstream release 0.56.0

* Fri May 30 2025 Packit Team <hello@packit.dev> - 0.55.0-1
- New upstream release 0.55.0

* Fri May 09 2025 Packit Team <hello@packit.dev> - 0.54.0-1
- New upstream release 0.54.0

* Fri Apr 04 2025 Packit Team <hello@packit.dev> - 0.53.0-1
- New upstream release 0.53.0

* Mon Mar 31 2025 Packit Team <hello@packit.dev> - 0.52.1-1
- New upstream release 0.52.1

* Fri Mar 28 2025 Packit Team <hello@packit.dev> - 0.52.0-1
- New upstream release 0.52.0

* Sun Mar 02 2025 Packit Team <hello@packit.dev> - 0.51.0-1
- New upstream release 0.51.0

* Fri Feb 07 2025 Packit Team <hello@packit.dev> - 0.50.4-1
- New upstream release 0.50.4

* Fri Jan 10 2025 Packit Team <hello@packit.dev> - 0.50.3-1
- New upstream release 0.50.3

* Fri Oct 25 2024 Packit Team <hello@packit.dev> - 0.50.2-1
- New upstream release 0.50.2

* Fri Oct 11 2024 Packit Team <hello@packit.dev> - 0.50.1-1
- New upstream release 0.50.1

* Fri Sep 13 2024 Packit Team <hello@packit.dev> - 0.50.0-1
- New upstream release 0.50.0

* Fri Mar 08 2024 Packit Team <hello@packit.dev> - 0.49.2-1
- New upstream release 0.49.2

* Mon Feb 12 2024 Packit Team <hello@packit.dev> - 0.49.1-1
- New upstream release 0.49.1

* Fri Jan 26 2024 Packit Team <hello@packit.dev> - 0.49.0-1
- New upstream release 0.49.0

* Sun Jan 07 2024 Packit Team <hello@packit.dev> - 0.48.1-1
- New upstream release 0.48.1

* Thu Dec 21 2023 Packit Team <hello@packit.dev> - 0.48.0-1
- New upstream release 0.48.0

* Sun Oct 29 2023 Packit Team <hello@packit.dev> - 0.47.1-1
- New upstream release 0.47.1

* Wed Oct 11 2023 Packit Team <hello@packit.dev> - 0.47.0-1
- New upstream release 0.47.0

* Fri Oct 06 2023 Packit Team <hello@packit.dev> - 0.46.2-1
- New upstream release 0.46.2

* Fri Oct 06 2023 Packit Team <hello@packit.dev> - 0.46.1-1
- New upstream release 0.46.1

* Fri Sep 08 2023 Packit Team <hello@packit.dev> - 0.46.0-1
- New upstream release 0.46.0

* Fri Aug 04 2023 Tomas Tomecek <ttomecek@redhat.com> - 0.45.0-2
- Confirm License is SPDX compatible.

* Mon Jun 05 2023 Packit Team <hello@packit.dev> - 0.45.0-1
- New upstream release 0.45.0

* Sun Mar 05 2023 Packit Team <hello@packit.dev> - 0.44.0-1
- New upstream release 0.44.0

* Thu Feb 23 2023 Packit Team <hello@packit.dev> - 0.43.0-1
- New upstream release 0.43.0

* Mon Jan 16 2023 Packit Team <hello@packit.dev> - 0.42.0-1
- New upstream release 0.42.0

* Thu Oct 27 2022 Packit Team <hello@packit.dev> - 0.41.0-1
- New upstream release 0.41.0

* Fri Sep 16 2022 Packit Team <hello@packit.dev> - 0.40.0-1
- New upstream release 0.40.0

* Wed Sep 07 2022 Packit Team <hello@packit.dev> - 0.39.0-1
- New upstream release 0.39.0

* Fri Apr 29 2022 Frantisek Lachman <flachman@redhat.com> - 0.38.1-1
- New upstream release 0.38.1

* Thu Apr 28 2022 František Nečas <fnecas@redhat.com> - 0.38.0-1
- New upstream release 0.38.0

* Wed Mar 30 2022 Laura Barcziova <lbarczio@redhat.com> - 0.37.0-1
- New upstream release 0.37.0

* Wed Mar 16 2022 František Nečas <fnecas@redhat.com> - 0.36.0-1
- New upstream release 0.36.0

* Wed Feb 16 2022 Maja Massarini <mmassari@redhat.com> - 0.35.0-1
- New upstream release 0.35.0

* Tue Jan 04 2022 Tomas Tomecek <ttomecek@redhat.com> - 0.34.0-1
- New upstream release 0.34.0

* Fri Dec 10 2021 Matej Focko <mfocko@redhat.com> - 0.33.0-1
- New upstream release 0.33.0

* Thu Nov 18 2021 František Nečas <fnecas@redhat.com> - 0.32.0-1
- New upstream release 0.32.0

* Wed Oct 27 2021 Tomas Tomecek <ttomecek@redhat.com> - 0.31.0-1
- New upstream release 0.31.0

* Thu Sep 30 2021 Hunor Csomortáni <csomh@redhat.com> - 0.30.0-1
- New upstream release 0.30.0

* Wed Sep 15 2021 Tomas Tomecek <ttomecek@redhat.com> - 0.29.0-1
- New upstream release 0.29.0

* Mon Aug 09 2021 Matej Focko <mfocko@redhat.com> - 0.28.0-1
- New upstream release 0.28.0

* Thu Jul 15 2021 Jiri Popelka <jpopelka@redhat.com> - 0.27.0-1
- New upstream release 0.27.0

* Fri Jun 11 2021 Tomas Tomecek <ttomecek@redhat.com> - 0.26.0-1
- New upstream release 0.26.0

* Tue Jun 01 2021 Laura Barcziova <lbarczio@redhat.com> - 0.25.0-1
- New upstream release 0.25.0

* Tue Apr 27 2021 Matej Mužila <mmuzila@redhat.com> - 0.24.1-1
- New upstream release 0.24.1

* Fri Apr 23 2021 Matej Mužila <mmuzila@redhat.com> - 0.24.0-1
- New upstream release 0.24.0

* Thu Mar 18 2021 Jiri Popelka <jpopelka@redhat.com> - 0.23.0-1
- New upstream release 0.23.0

* Fri Feb 19 2021 Matej Focko <mfocko@redhat.com> - 0.21.0-1
- New upstream release 0.21.0

* Thu Feb 04 2021 Matej Focko <mfocko@redhat.com> - 0.20.0-1
- New upstream release 0.20.0

* Thu Jan  7 10:52:27 CET 2021 Tomas Tomecek <ttomecek@redhat.com> - 0.19.0-1
- New upstream release 0.19.0

* Wed Dec 09 2020 Jan Sakalos <sakalosj@gmail.com> - 0.18.1-1
- New upstream release 0.18.1

* Tue Oct 27 2020 Jiri Popelka <jpopelka@redhat.com> - 0.18.0-1
- New upstream release 0.18.0

* Wed Sep 30 2020 Matej Focko <mfocko@redhat.com> - 0.16.0-1
- New upstream release 0.16.0

* Wed Sep 16 2020 Tomas Tomecek <ttomecek@redhat.com> - 0.15.0-1
- New upstream release 0.15.0

* Tue Sep 01 2020 Dominika Hodovska <dhodovsk@redhat.com> - 0.14.0-1
- New upstream release 0.14.0

* Wed Aug 19 2020 Jan Sakalos <sakalosj@gmail.com> - 0.13.1-1
- New upstream release 0.13.1

* Wed Aug 05 2020 Jan Sakalos <sakalosj@gmail.com> - 0.13.0-1
- New upstream release 0.13.0

* Thu Jul 09 2020 Jiri Popelka <jpopelka@redhat.com> - 0.12.2-1
- New upstream release 0.12.2

* Wed May 27 2020 Dominika Hodovska <dhodovsk@redhat.com> - 0.12.1-1
- New upstream release 0.12.1

* Wed May 06 2020 Frantisek Lachman <flachman@redhat.com> - 0.12.0-1
- New upstream release 0.12.0

* Fri Apr 17 2020 Frantisek Lachman <flachman@redhat.com> - 0.11.2-1
- New upstream release 0.11.2

* Wed Apr 01 2020 Jan Sakalos <sakalosj@gmail.com> - 0.11.1-1
- patch release: 0.11.1

* Sat Mar 07 2020 Jiri Popelka <jpopelka@redhat.com> - 0.11.0-1
- New upstream release 0.11.0

* Tue Jan 28 2020 Frantisek Lachman <flachman@redhat.com> - 0.10.0-1
- New upstream release 0.10.0

* Wed Dec 04 2019 Frantisek Lachman <flachman@redhat.com> - 0.9.0-1
- New upstream release 0.9.0

* Mon Sep 30 2019 Frantisek Lachman <flachman@redhat.com> - 0.8.0-1
- New upstream release 0.8.0

* Wed Sep 11 2019 Frantisek Lachman <flachman@redhat.com> - 0.7.0-1
- New upstream release 0.7.0

* Tue Jul 23 2019 Frantisek Lachman <flachman@redhat.com> - 0.6.0-1
- New upstream release 0.6.0

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
