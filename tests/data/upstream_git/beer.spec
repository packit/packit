%global upstream_name beerware

# some change

Name:           beer
Version:        0.1.0
Release:        1%{?dist}
Summary:        A tool to make you happy

License:        Beerware
Source0:         %{upstream_name}-%{version}.tar.gz
BuildArch:      noarch

### patches ###

%description
...but not too happy.

%prep
%autosetup -n %{upstream_name}-%{version}

%changelog
* Mon Feb 25 2019 Tomas Tomecek <ttomecek@redhat.com> - 0.1.0-1
- Initial brewing

* Sun Feb 24 2019 Tomas Tomecek <ttomecek@redhat.com> - 0.0.0-1
- No brewing, yet.
