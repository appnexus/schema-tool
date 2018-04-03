Summary: Schema Tool
Name: schema-tool
Version: 0
Release: 1
License: AppNexus, Inc.
Group: Applications/Internet
Source: schema-tool-%{version}.tar.gz
Vendor: AppNexus, Inc.
Packager: DevOps <devops@appnexus.com>
Requires: python2.7
BuildRoot: %{_tmppath}/%{name}-%{version}-buildroot

%description
A schema tool to manage alters and migrations.

%prep
%setup -q

%build

%install
mkdir -p %{buildroot}/usr/local/adnxs/schema-tool/
mkdir -p %{buildroot}/usr/bin
cp -R * %{buildroot}/usr/local/adnxs/schema-tool/
ln -s /usr/local/adnxs/schema-tool/schema %{buildroot}/usr/bin/schema

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root)
/usr/local/adnxs/schema-tool/
/usr/bin/schema
