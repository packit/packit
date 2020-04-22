%global upstream_name beerware

Name:           beer
Version:        0.1.0
Release:        1%{?dist}
Summary:        A tool to make you happy

License:        Beerware
Source:         %{upstream_name}-%{version}.tar.gz
BuildArch:      noarch

%description
...but not too happy.

%prep
%autosetup -n %{upstream_name}-%{version}

%changelog
* Mon Feb 25 2019 Tomas Tomecek <ttomecek@redhat.com> - 0.1.0-1
- Initial brewing
