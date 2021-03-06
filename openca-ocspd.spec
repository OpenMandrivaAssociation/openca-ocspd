%define ssldir %{_sysconfdir}/pki/ocspd

Summary:	OpenCA OCSP Daemon
Name:		openca-ocspd
Version:	1.5.1
Release:	0.rc1.9
License:	BSD-like
Group:		System/Servers
URL:		https://www.openca.org/projects/ocspd/
Source0:	%{name}-%{version}-rc1.tar.gz
Source1:	ocspd.service
Source2:	examples.tar.bz2
Source3:	ocspd-mkcert.sh
Source4:	ocspd.cnf
Patch0:		OpenCA-OCSPD-1.1.0a-mdv_config.diff
Patch1:		openca-ocspd-autoconf_fixes.diff
Patch2:		openca-ocspd-1.5.1-rc1-format_not_a_string_literal_and_no_format_arguments.diff
Patch3:		openca-ocspd-1.5.1-openssl.patch
Requires(post): rpm-helper
Requires(preun): rpm-helper
Requires(pre): rpm-helper
Requires(postun): rpm-helper
BuildRequires:	openssl-devel >= 0.9.7
BuildRequires:  openldap-devel
BuildRequires:  sasl-devel
BuildRequires:	automake
BuildRequires:	autoconf2.5
BuildRequires: systemd
Requires(pre): systemd
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd

%description
The openca-ocspd is an RFC2560 compliant OCSPD responder. It can be used to
verify the status of a certificate using OCSP clients (such as
Mozilla/Netscape7).

This product includes OpenCA software written by Massimiliano Pala
(madwolf@openca.org) and the OpenCA Group (www.openca.org)

%prep
%setup -q -n %{name}-%{version}-rc1 -a2

# fix strange perms
find . -type d -perm 0700 -exec chmod 755 {} \;
find . -type f -perm 0555 -exec chmod 755 {} \;
find . -type f -perm 0444 -exec chmod 644 {} \;

%patch0 -p1
%patch1 -p0
%patch2 -p0
%patch3 -p1

cp %{SOURCE3} ocspd-mkcert.sh
cp %{SOURCE4} ocspd.cnf

%build
%serverbuild

export CFLAGS="$CFLAGS -DLDAP_DEPRECATED"

export WANT_AUTOCONF_2_5=1
autoreconf -fi
%configure2_5x \
    --enable-openldap \
    --enable-openssl-engine \
    --disable-semaphores \
    --enable-flock \
    --with-openssl-prefix=%{_prefix} \
    --with-openldap-prefix=%{_prefix} \
    --with-ocspd-user=ocspd \
    --with-ocspd-group=ocspd \
    --with-openca-prefix=%{_datadir}/openca

# lib64 fix
find -type f -name "Makefile" | xargs perl -pi -e "s|%{_prefix}/lib|%{_libdir}|g"

%make

%install
# don't fiddle with the initscript!
export DONT_GPRINTIFY=1

install -d %{buildroot}%{_unitdir}
install -d %{buildroot}%{ssldir}/{certs,crls,private}
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
install -D -p -m 0755 %{SOURCE1} %{buildroot}%{_unitdir}/ocspd.service

cat > ocspd.sysconfig << EOF
# put options here
#OCSPD_OPTIONS=""
EOF

install -m0644 ocspd.sysconfig %{buildroot}%{_sysconfdir}/sysconfig/ocspd

# install some example certs
install -m0600 examples/certs/cacert.pem %{buildroot}%{ssldir}/certs/
install -m0600 examples/certs/key.pem %{buildroot}%{ssldir}/certs/
install -m0600 examples/certs/ocspcert.pem %{buildroot}%{ssldir}/certs/
install -m0600 examples/certs/ocsp_key.pem %{buildroot}%{ssldir}/certs/
install -m0600 examples/certs/ocsp.pem %{buildroot}%{ssldir}/certs/

# fix ssl stuff
touch %{buildroot}%{ssldir}/certs/ocspd_cert.pem
touch %{buildroot}%{ssldir}/private/ocspd_key.pem
touch %{buildroot}%{ssldir}/index.txt
chmod 600 %{buildroot}%{ssldir}/certs/ocspd_cert.pem
chmod 600 %{buildroot}%{ssldir}/private/ocspd_key.pem
chmod 600 %{buildroot}%{ssldir}/index.txt
echo "01" > %{buildroot}%{ssldir}/serial

install -m0644 ocspd.cnf %{buildroot}%{ssldir}/ocspd.cnf
install -m0755 ocspd-mkcert.sh %{buildroot}%{ssldir}/mkcert.sh

# fix %%{ssldir}
find %{buildroot}%{_sysconfdir} -type f | xargs perl -pi -e "s|/etc/ssl/ocspd|%{ssldir}|g"

%pre
%systemd_pre ocspd.service

%post
%systemd_post ocspd.service
# create a dummy ssl cert
if [ ! -f %{ssldir}/certs/ocspd_key.pem ]; then
    %{ssldir}/mkcert.sh \
    OPENSSL=%{_bindir}/openssl \
    SSLDIR=%{ssldir} \
    OPENSSLCONFIG=%{ssldir}/ocspd.cnf \
    CERTFILE=%{ssldir}/certs/ocspd_cert.pem \
    KEYFILE=%{ssldir}/private/ocspd_key.pem &> /dev/null
fi

%preun
%systemd_preun ocspd.service

%postun
%systemd_postun_with_restart ocspd.service

%clean

%files
%doc AUTHORS COPYING ChangeLog README
%doc examples/index.txt examples/ocspd.conf examples/request.sh
%{_unitdir}/ocspd.service
%config(noreplace) %attr(0640,ocspd,ocspd) %{_sysconfdir}/ocspd.conf*
%config(noreplace) %attr(0640,root,root) %{_sysconfdir}/sysconfig/ocspd
%dir %attr(0750,ocspd,ocspd) %{ssldir}
%attr(0644,root,root) %config(noreplace) %{ssldir}/ocspd.cnf
%attr(0754,root,root) %{ssldir}/mkcert.sh
%dir %attr(0750,ocspd,ocspd) %{ssldir}/certs
%dir %attr(0750,ocspd,ocspd) %{ssldir}/crls
%dir %attr(0750,ocspd,ocspd) %{ssldir}/private
%attr(0600,ocspd,ocspd) %ghost %config(missingok,noreplace) %verify(not md5 size mtime) %{ssldir}/certs/ocspd_cert.pem
%attr(0600,ocspd,ocspd) %ghost %config(missingok,noreplace) %verify(not md5 size mtime) %{ssldir}/private/ocspd_key.pem
%attr(0600,ocspd,ocspd) %ghost %config(missingok,noreplace) %verify(not md5 size mtime) %{ssldir}/index.txt
%attr(0600,ocspd,ocspd) %ghost %config(missingok,noreplace) %verify(not md5 size mtime) %{ssldir}/serial
%attr(0600,ocspd,ocspd) %config(noreplace) %verify(not md5 size mtime) %{ssldir}/certs/cacert.pem
%attr(0600,ocspd,ocspd) %config(noreplace) %verify(not md5 size mtime) %{ssldir}/certs/key.pem
%attr(0600,ocspd,ocspd) %config(noreplace) %verify(not md5 size mtime) %{ssldir}/certs/ocsp.pem
%attr(0600,ocspd,ocspd) %config(noreplace) %verify(not md5 size mtime) %{ssldir}/certs/ocsp_key.pem
%attr(0600,ocspd,ocspd) %config(noreplace) %verify(not md5 size mtime) %{ssldir}/certs/ocspcert.pem
%attr(0755,root,root) %{_sbindir}/ocspd
%attr(0755,ocspd,ocspd) %dir /var/run/ocspd
%attr(0755,ocspd,ocspd) %dir %{_localstatedir}/lib/ocspd
%{_mandir}/man3/ocspd*
