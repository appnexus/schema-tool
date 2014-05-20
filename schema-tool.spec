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
mkdir -p %{buildroot}/usr/local/bin/schema-tool
cp -R * %{buildroot}/usr/local/bin/schema-tool
ln -s /usr/local/bin/schema-tool/schema.py %{buildroot}/usr/bin/schema

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root)
/usr/local/bin/schema-tool/%{version}
