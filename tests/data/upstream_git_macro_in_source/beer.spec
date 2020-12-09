%global upstream_name beerware
%global some_hash cheers
%global some_release 11

# some change

Name:           beer
Version:        0.1.%{some_hash}
Release:        %{some_release}
Summary:        A tool to make you happy

License:        Beerware
Source:         %{upstream_name}-%{some_hash}-%{some_release}-8.6.tar.gz
BuildArch:      noarch

%description
...but not too happy.

%prep
%autosetup -n %{upstream_name}-%{version}

%changelog
* Mon Feb 25 2019 Tomas Tomecek <ttomecek@redhat.com> - 0.1.0-1
- Initial brewing
