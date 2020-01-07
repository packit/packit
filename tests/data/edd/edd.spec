Name: edd
Version: 0.3
Release: 1%{?dist}

Summary: Always use your favorite text editor, anywhere.
License: GPLv2+

URL: http://psss.fedorapeople.org/edd/
Source0: http://psss.fedorapeople.org/edd/download/%{name}-%{version}.tar.bz2

BuildArch: noarch
Requires: xclip

%description
Edd is a tiny script which allows to easily edit content of the
clipboard with a single keyboard shortcut. In this way Edd allows
you to always use your favorite text editor, wherever you need.

%prep
%setup -q

%build

%install
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_mandir}/man1
install -pm 755 edd %{buildroot}%{_bindir}
install -pm 644 docs/*.1.gz %{buildroot}%{_mandir}/man1

%files
%{_mandir}/man1/*
%{_bindir}/edd
%doc README.rst
%{!?_licensedir:%global license %%doc}
%license LICENSE

%changelog
* Tue Sep 01 2015 Petr Šplíchal <psplicha@redhat.com> 0.3-1
- Support for simple config, documentation update
- Strip trailing newlines from edited text
- Bail out if no file selected with --list [fix #5]
- Document the Ctrl-Shift-V keyboard shortcut

* Fri Aug 28 2015 Petr Šplíchal <psplicha@redhat.com> 0.2-1
- Document new options, some adjustments
- New option --last, some reorganization [fix #1]
- Work around RHEL7 zenity bug [BZ#1060471]
- Use the primary mouse selection first [fix #2]
- Option --list, fixing issue #3

* Tue Aug 25 2015 Petr Šplíchal <psplicha@redhat.com> 0.1-1
- Initial packaging.
