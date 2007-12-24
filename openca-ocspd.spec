%if %mdkversion >= 200610
%define ssldir %{_sysconfdir}/pki/ocspd
%else
%define ssldir %{_sysconfdir}/ssl/ocspd
%endif

Summary:	OpenCA OCSP Daemon
Name:		openca-ocspd
Version:	1.5.1
Release:	%mkrel 0.rc1.2
License:	GPL
Group:		System/Servers
URL:		http://www.openca.org/
Source0:	%{name}-%{version}-rc1.tar.gz
Source1:	ocspd.init
Source2:	examples.tar.bz2
Source3:	ocspd-mkcert.sh
Source4:	ocspd.cnf
Patch0:		OpenCA-OCSPD-1.1.0a-mdv_config.diff
Requires(post): rpm-helper
Requires(preun): rpm-helper
Requires(pre): rpm-helper
Requires(postun): rpm-helper
BuildRequires:	openssl-devel >= 0.9.7
BuildRequires:  openldap-devel
BuildRequires:  libsasl-devel
BuildRequires:	automake1.7
BuildRequires:	autoconf2.5
BuildRoot:	%{_tmppath}/%{name}-%{version}-root

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

cp %{SOURCE1} ocspd.init
cp %{SOURCE3} ocspd-mkcert.sh
cp %{SOURCE4} ocspd.cnf

%build
%serverbuild

export CFLAGS="$CFLAGS -DLDAP_DEPRECATED"

export WANT_AUTOCONF_2_5=1
rm -f configure
libtoolize --copy --force
aclocal-1.7 -I build --output=build/aclocal.m4
aclocal-1.7 -I build 
automake-1.7 --add-missing --copy --gnu
autoconf --force

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
[ -n "%{buildroot}" -a "%{buildroot}" != / ] && rm -rf %{buildroot}

# don't fiddle with the initscript!
export DONT_GPRINTIFY=1

install -d %{buildroot}%{_initrddir}
install -d %{buildroot}%{ssldir}/{certs,crls,private}
install -d %{buildroot}%{_sysconfdir}/sysconfig
install -d %{buildroot}%{_localstatedir}/ocspd

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
%_pre_useradd ocspd /dev/null /bin/false

%post
# create a dummy ssl cert
if [ ! -f %{ssldir}/certs/ocspd_key.pem ]; then
    %{ssldir}/mkcert.sh \
    OPENSSL=%{_bindir}/openssl \
    SSLDIR=%{ssldir} \
    OPENSSLCONFIG=%{ssldir}/ocspd.cnf \
    CERTFILE=%{ssldir}/certs/ocspd_cert.pem \
    KEYFILE=%{ssldir}/private/ocspd_key.pem &> /dev/null
fi
%_post_service ocspd

%preun
%_preun_service ocspd

%postun
%_postun_userdel ocspd

%clean
[ -n "%{buildroot}" -a "%{buildroot}" != / ] && rm -rf %{buildroot}

%files
%defattr(-,root,root)
%doc AUTHORS COPYING ChangeLog README
%doc examples/index.txt examples/ocspd.conf examples/request.sh
%attr(0755,root,root) %{_initrddir}/ocspd
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
%attr(0755,ocspd,ocspd) %dir %{_localstatedir}/ocspd
%{_mandir}/man3/ocspd*
