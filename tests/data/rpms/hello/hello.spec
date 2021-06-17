Name: hello
Version: 1.0.1
Release: 1%{?dist}
Summary: Hello World application written in Rust
License: MIT

URL: src/hello
Source: hello-1.0.1.tar.gz

# Say hello to Fedora
Patch: turn-into-fedora.patch

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
