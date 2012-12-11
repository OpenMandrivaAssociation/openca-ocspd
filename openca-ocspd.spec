%if %mdkversion >= 200610
%define ssldir %{_sysconfdir}/pki/ocspd
%else
%define ssldir %{_sysconfdir}/ssl/ocspd
%endif

Summary:	OpenCA OCSP Daemon
Name:		openca-ocspd
Version:	1.5.1
Release:	%mkrel 0.rc1.8
License:	BSD-like
Group:		System/Servers
URL:		https://www.openca.org/projects/ocspd/
Source0:	%{name}-%{version}-rc1.tar.gz
Source1:	ocspd.init
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
BuildRequires:  libsasl-devel
BuildRequires:	automake
BuildRequires:	autoconf2.5
BuildRoot:	%{_tmppath}/%{name}-%{version}-%{release}-buildroot

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

cp %{SOURCE1} ocspd.init
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
rm -rf %{buildroot}

# don't fiddle with the initscript!
export DONT_GPRINTIFY=1

install -d %{buildroot}%{_initrddir}
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
rm -rf %{buildroot}

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
%attr(0755,ocspd,ocspd) %dir %{_localstatedir}/lib/ocspd
%{_mandir}/man3/ocspd*


%changelog
* Mon Jan 03 2011 Oden Eriksson <oeriksson@mandriva.com> 1.5.1-0.rc1.8mdv2011.0
+ Revision: 627815
- don't force the usage of automake1.7

* Tue Dec 07 2010 Oden Eriksson <oeriksson@mandriva.com> 1.5.1-0.rc1.7mdv2011.0
+ Revision: 613529
- rebuild

* Wed Apr 28 2010 Funda Wang <fwang@mandriva.org> 1.5.1-0.rc1.6mdv2010.1
+ Revision: 540007
- add fedora patch to build with openssl 1.0.0

* Mon Oct 05 2009 Oden Eriksson <oeriksson@mandriva.com> 1.5.1-0.rc1.5mdv2010.0
+ Revision: 454024
- P2: fix format string errors
- rebuild

  + Thierry Vignaud <tv@mandriva.org>
    - rebuild

* Mon Jul 14 2008 Oden Eriksson <oeriksson@mandriva.com> 1.5.1-0.rc1.3mdv2009.0
+ Revision: 234500
- fix build

  + Pixel <pixel@mandriva.com>
    - adapt to %%_localstatedir now being /var instead of /var/lib (#22312)

* Mon Dec 24 2007 Oden Eriksson <oeriksson@mandriva.com> 1.5.1-0.rc1.2mdv2008.1
+ Revision: 137521
- rebuilt against openldap-2.4.7 libs

  + Olivier Blin <oblin@mandriva.com>
    - restore BuildRoot

  + Thierry Vignaud <tv@mandriva.org>
    - kill re-definition of %%buildroot on Pixel's request

* Fri Aug 17 2007 Oden Eriksson <oeriksson@mandriva.com> 1.5.1-0.rc1.1mdv2008.0
+ Revision: 65028
- 1.5.1-rc1
- bunzip sources


* Fri Mar 02 2007 Oden Eriksson <oeriksson@mandriva.com> 1.1.1-1mdv2007.0
+ Revision: 131155
- Import openca-ocspd

* Thu Jul 20 2006 Oden Eriksson <oeriksson@mandriva.com> 1.1.1-1mdv2007.0
- 1.1.1 (Minor bugfixes)

* Thu Mar 02 2006 Oden Eriksson <oeriksson@mandriva.com> 1.1.0a-1mdk
- 1.1.0a
- fix the default config (P0)
- fix the initscript (S1)
- misc spec file fixes
- generate ssl pem files in %%post
- fix lock file directory (don't use sysv ipc semaphores, P1)

* Wed Nov 30 2005 Oden Eriksson <oeriksson@mandriva.com> 1.0.5-2mdk
- rebuilt against openssl-0.9.8a

* Fri Nov 11 2005 Oden Eriksson <oeriksson@mandriva.com> 1.0.5-1mdk
- 1.0.5

* Wed Aug 31 2005 Oden Eriksson <oeriksson@mandriva.com> 1.0.3-3mdk
- rebuilt against new openldap-2.3.6 libs

* Mon Aug 29 2005 Oden Eriksson <oeriksson@mandriva.com> 1.0.3-2mdk
- fix deps
- fix the ocspd.sysconfig file, duh!

* Thu Jun 23 2005 Oden Eriksson <oeriksson@mandrakesoft.com> 1.0.3-1mdk
- 1.0.3
- rediff P0
- fix deps
- fix rpmlint errors
- fix naming of the initscript and such

* Tue Feb 08 2005 Buchan Milne <bgmilne@linux-mandrake.com> 0.6.5-3mdk
- rebuild for ldap2.2_7

* Fri Feb 04 2005 Oden Eriksson <oeriksson@mandrakesoft.com> 0.6.5-2mdk
- rebuilt against new openldap libs

* Sun Jan 30 2005 Oden Eriksson <oeriksson@mandrakesoft.com> 0.6.5-1mdk
- 0.6.5

* Tue Jan 18 2005 Oden Eriksson <oeriksson@mandrakesoft.com> 0.6.4-1mdk
- 0.6.4
- added one lib64 fix

* Wed Jan 05 2005 Oden Eriksson <oeriksson@mandrakesoft.com> 0.6.2-1mdk
- 0.6.2

* Fri Aug 27 2004 Oden Eriksson <oeriksson@mandrakesoft.com> 0.6.1-1mdk
- 0.6.1
- rediff P0
- added S2 taken from openca-ocspd-0.5.1
- misc spec file fixes

* Fri Aug 27 2004 Oden Eriksson <oeriksson@mandrakesoft.com> 0.5.1-0.3mdk
- new tarball, same version

* Mon Jul 12 2004 Oden Eriksson <oeriksson@mandrakesoft.com> 0.5.1-0.2mdk
- built for cooker

* Tue May 25 2004 Oden Eriksson <oeriksson@mandrakesoft.com> 0.5.1-0.1mdk
- use a cvs snap

* Wed May 05 2004 Oden Eriksson <oeriksson@mandrakesoft.com> 0.4.2-1mdk
- initial Mandrake package, used bits and pieces from the provided spec
  files and also from the latest work by Michael Bell
- added P0 and S1

