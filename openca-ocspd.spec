Summary:	OpenCA OCSP Daemon
Name:		openca-ocspd
Version:	2.1.0
Release:	%mkrel 1
License:	BSD-like
Group:		System/Servers
URL:		https://www.openca.org/projects/ocspd/
Source0:	%{name}-%{version}.tar.gz
Source1:	ocspd.init
Source2:	examples.tar.bz2
Source3:	ocspd-mkcert.sh
Source4:	ocspd.cnf
Patch0:		openca-ocspd-2.1.0-fhs.diff
Patch1:		openca-ocspd-2.1.0-mdv_conf.diff
Patch2:		openca-ocspd-2.1.0-format_not_a_string_literal_and_no_format_arguments.diff
Requires(post): rpm-helper
Requires(preun): rpm-helper
Requires(pre): rpm-helper
Requires(postun): rpm-helper
BuildRequires:	openssl-devel >= 0.9.7
BuildRequires:  openldap-devel
BuildRequires:  libsasl-devel
BuildRequires:	automake
BuildRequires:	autoconf2.5
BuildRequires:	pki-devel >= 0.6.3
BuildRoot:	%{_tmppath}/%{name}-%{version}-%{release}-buildroot

%description
The openca-ocspd is an RFC2560 compliant OCSPD responder. It can be used to
verify the status of a certificate using OCSP clients (such as
Mozilla/Netscape7).

This product includes OpenCA software written by Massimiliano Pala
(madwolf@openca.org) and the OpenCA Group (www.openca.org)

%prep

%setup -q -n %{name}-%{version} -a2

# fix strange perms
find . -type d -perm 0700 -exec chmod 755 {} \;
find . -type f -perm 0555 -exec chmod 755 {} \;
find . -type f -perm 0444 -exec chmod 644 {} \;

%patch0 -p0
%patch1 -p0
%patch2 -p0

cp %{SOURCE1} ocspd.init
cp %{SOURCE3} ocspd-mkcert.sh
cp %{SOURCE4} ocspd.cnf

%build
%serverbuild

export WANT_AUTOCONF_2_5=1
mkdir -p m4
autoreconf -fi

%configure2_5x \
    --disable-semaphores \
    --enable-flock \
    --enable-debug \
    --with-ocspd-user=ocspd \
    --with-ocspd-group=ocspd \
    --with-openca-prefix=%{_datadir}/openca

make

%install
rm -rf %{buildroot}

# don't fiddle with the initscript!
export DONT_GPRINTIFY=1

install -d %{buildroot}%{_initrddir}
install -d %{buildroot}%{_sysconfdir}/pki/ocspd/{certs,crls,private}
install -d %{buildroot}%{_sysconfdir}/sysconfig
install -d %{buildroot}%{_localstatedir}/lib/ocspd

make \
    DEST_BINDIR="%{buildroot}%{_bindir}" \
    DEST_DATADIR="%{buildroot}%{_datadir}/openca" \
    DEST_LIBDIR="%{buildroot}%{_libdir}" \
    DEST_MANDIR="%{buildroot}%{_mandir}" \
    DEST_SBINDIR="%{buildroot}%{_sbindir}" \
    DESTDIR="%{buildroot}" \
    install

# fix pid dir
install -d %{buildroot}/var/run/ocspd

# install a nicer sysv script
rm -rf %{buildroot}%{_sysconfdir}/init.d
rm -f %{buildroot}%{_initrddir}/ocspd
install -m0755 ocspd.init %{buildroot}%{_initrddir}/ocspd

cat > ocspd.sysconfig << EOF
# put options here
#OCSPD_OPTIONS=""
EOF

install -m0644 ocspd.sysconfig %{buildroot}%{_sysconfdir}/sysconfig/ocspd

# install some example certs
install -m0600 examples/certs/cacert.pem %{buildroot}%{_sysconfdir}/pki/ocspd/certs/
install -m0600 examples/certs/key.pem %{buildroot}%{_sysconfdir}/pki/ocspd/certs/
install -m0600 examples/certs/ocspcert.pem %{buildroot}%{_sysconfdir}/pki/ocspd/certs/
install -m0600 examples/certs/ocsp_key.pem %{buildroot}%{_sysconfdir}/pki/ocspd/certs/
install -m0600 examples/certs/ocsp.pem %{buildroot}%{_sysconfdir}/pki/ocspd/certs/

# fix ssl stuff
touch %{buildroot}%{_sysconfdir}/pki/ocspd/certs/ocspd_cert.pem
touch %{buildroot}%{_sysconfdir}/pki/ocspd/private/ocspd_key.pem
touch %{buildroot}%{_sysconfdir}/pki/ocspd/index.txt
chmod 600 %{buildroot}%{_sysconfdir}/pki/ocspd/certs/ocspd_cert.pem
chmod 600 %{buildroot}%{_sysconfdir}/pki/ocspd/private/ocspd_key.pem
chmod 600 %{buildroot}%{_sysconfdir}/pki/ocspd/index.txt
echo "01" > %{buildroot}%{_sysconfdir}/pki/ocspd/serial

install -m0644 ocspd.cnf %{buildroot}%{_sysconfdir}/pki/ocspd/ocspd.cnf
install -m0755 ocspd-mkcert.sh %{buildroot}%{_sysconfdir}/pki/ocspd/mkcert.sh

# nuke useless cruft
rm -f %{buildroot}%{_bindir}/ocspd-genreq.sh
rm -f %{buildroot}%{_bindir}/test.sh
rm -f %{buildroot}%{_libdir}/pkgconfig/openca-ocspd.pc

# move /etc/pki/ocspd/ocspd.xml in place
mv %{buildroot}%{_sysconfdir}/pki/ocspd/ocspd.xml %{buildroot}%{_sysconfdir}/ocspd.xml

%pre
%_pre_useradd ocspd /dev/null /bin/false

%post
# create a dummy ssl cert
if [ ! -f %{_sysconfdir}/pki/ocspd/certs/ocspd_key.pem ]; then
    %{_sysconfdir}/pki/ocspd/mkcert.sh \
    OPENSSL=%{_bindir}/openssl \
    SSLDIR=%{_sysconfdir}/pki/ocspd \
    OPENSSLCONFIG=%{_sysconfdir}/pki/ocspd/ocspd.cnf \
    CERTFILE=%{_sysconfdir}/pki/ocspd/certs/ocspd_cert.pem \
    KEYFILE=%{_sysconfdir}/pki/ocspd/private/ocspd_key.pem &> /dev/null
fi
%_post_service ocspd

%preun
%_preun_service ocspd

%postun
%_postun_userdel ocspd

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root)
%doc AUTHORS COPYING ChangeLog README
%doc examples/index.txt examples/ocspd.conf examples/request.sh
%attr(0755,root,root) %{_initrddir}/ocspd
%config(noreplace) %attr(0640,ocspd,ocspd) %{_sysconfdir}/ocspd.xml
%config(noreplace) %attr(0640,root,root) %{_sysconfdir}/sysconfig/ocspd
%dir %attr(0750,ocspd,ocspd) %{_sysconfdir}/pki/ocspd
%attr(0644,root,root) %config(noreplace) %{_sysconfdir}/pki/ocspd/ocspd.cnf
%attr(0754,root,root) %{_sysconfdir}/pki/ocspd/mkcert.sh
%dir %attr(0750,ocspd,ocspd) %{_sysconfdir}/pki/ocspd/certs
%dir %attr(0750,ocspd,ocspd) %{_sysconfdir}/pki/ocspd/crls
%dir %attr(0750,ocspd,ocspd) %{_sysconfdir}/pki/ocspd/private
%dir %attr(0750,ocspd,ocspd) %{_sysconfdir}/pki/ocspd/ca.d
%dir %attr(0750,ocspd,ocspd) %{_sysconfdir}/pki/ocspd/pki
%dir %attr(0750,ocspd,ocspd) %{_sysconfdir}/pki/ocspd/pki/token.d
%attr(0600,ocspd,ocspd) %ghost %config(missingok,noreplace) %verify(not md5 size mtime) %{_sysconfdir}/pki/ocspd/certs/ocspd_cert.pem
%attr(0600,ocspd,ocspd) %ghost %config(missingok,noreplace) %verify(not md5 size mtime) %{_sysconfdir}/pki/ocspd/private/ocspd_key.pem
%attr(0600,ocspd,ocspd) %ghost %config(missingok,noreplace) %verify(not md5 size mtime) %{_sysconfdir}/pki/ocspd/index.txt
%attr(0600,ocspd,ocspd) %ghost %config(missingok,noreplace) %verify(not md5 size mtime) %{_sysconfdir}/pki/ocspd/serial
%attr(0600,ocspd,ocspd) %config(noreplace) %verify(not md5 size mtime) %{_sysconfdir}/pki/ocspd/certs/cacert.pem
%attr(0600,ocspd,ocspd) %config(noreplace) %verify(not md5 size mtime) %{_sysconfdir}/pki/ocspd/certs/key.pem
%attr(0600,ocspd,ocspd) %config(noreplace) %verify(not md5 size mtime) %{_sysconfdir}/pki/ocspd/certs/ocsp.pem
%attr(0600,ocspd,ocspd) %config(noreplace) %verify(not md5 size mtime) %{_sysconfdir}/pki/ocspd/certs/ocsp_key.pem
%attr(0600,ocspd,ocspd) %config(noreplace) %verify(not md5 size mtime) %{_sysconfdir}/pki/ocspd/certs/ocspcert.pem
%attr(0600,ocspd,ocspd) %ghost %config(missingok,noreplace) %verify(not md5 size mtime) %{_sysconfdir}/pki/ocspd/ca.d/collegeca.xml
%attr(0600,ocspd,ocspd) %ghost %config(missingok,noreplace) %verify(not md5 size mtime) %{_sysconfdir}/pki/ocspd/pki/token.d/eracom.xml
%attr(0600,ocspd,ocspd) %ghost %config(missingok,noreplace) %verify(not md5 size mtime) %{_sysconfdir}/pki/ocspd/pki/token.d/etoken.xml
%attr(0600,ocspd,ocspd) %ghost %config(missingok,noreplace) %verify(not md5 size mtime) %{_sysconfdir}/pki/ocspd/pki/token.d/software.xml
%attr(0755,root,root) %{_sbindir}/ocspd
%attr(0755,ocspd,ocspd) %dir /var/run/ocspd
%attr(0755,ocspd,ocspd) %dir %{_localstatedir}/lib/ocspd
%{_mandir}/man3/ocspd*
