%global upstream_name beerware

Name:           beer
Version:        0.0.0
Release:        1%{?dist}
Summary:        A tool to make you happy

License:        Beerware
%if 0%{?fedora} >= 28 || 0%{?rhel} >= 8
Source0:        %{upstream_name}-%{version}.tar.gz
%endif
BuildArch:      noarch

%description
...but not too happy.

%prep
%autosetup -n %{upstream_name}-%{version}

%changelog
%autochangelog
