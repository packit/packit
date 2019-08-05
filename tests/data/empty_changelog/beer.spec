%global upstream_name beerware

Name:           beer
Version:        0.1.0
Release:        1%{?dist}
Summary:        A tool to make you happy

License:        Beerware
Source0:        %{upstream_name}-%{version}.tar.gz
BuildArch:      noarch

%description
...but not too happy.

%prep
%autosetup -n %{upstream_name}-%{version}
