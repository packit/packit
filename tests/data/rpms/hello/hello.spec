Name: hello
Version: 1.0.1
Release: 1%{?dist}
Summary: Hello World application written in Rust
License: MIT

URL: src/hello
Source: hello-1.0.1.tar.gz

# Say hello to Fedora
Patch0001: turn-into-fedora.patch

# Patch from Git
Patch0002: from-git.patch

# Funky patch
Patch0003: 0017-Patch-This..patch

Provides: hello

BuildRequires: make
BuildRequires: rust

%description
Hello World application written in Rust

%prep
%autosetup

%build
make hello

%install
install -Dpm0777 hello %{_bindir}/hello
