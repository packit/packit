Name:           beer
Version:        0.1.0
Release:        1%{?dist}
Summary:        A tool to make you happy

License:        Beerware
Source0:        beerware-%{version}.tar.gz
BuildArch:      noarch

%description
...but not too happy.

%prep
true

%changelog
* Mon Feb 25 2019 Tomas Tomecek <ttomecek@redhat.com> - 0.1.0-1
- Initial brewing
