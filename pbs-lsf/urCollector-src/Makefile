SHELL=/bin/sh
CC=c++
INSTALLDIR=/opt/urCollector
INSTALLDIR_LIBEXEC=$(INSTALLDIR)/libexec/
INSTALLDIR_SBIN=$(INSTALLDIR)/sbin/
INSTALLDIR_ETC=$(INSTALLDIR)/etc/
urCreator : urCreator.cpp urwg.cpp xmlUtil.cpp hlr_prot_errcode.h  int2string.h  stringSplit.h  urwg.h  xmlUtil.h
	$(CC) -o urCreator urCreator.cpp urwg.cpp xmlUtil.cpp 
	chmod +x urCreator
all: urCreator
install: urCreator
	[ -d $(INSTALLDIR) ] || mkdir $(INSTALLDIR);
	[ -d $(INSTALLDIR_LIBEXEC) ] || mkdir $(INSTALLDIR_LIBEXEC);
	[ -d $(INSTALLDIR_SBIN) ] || mkdir $(INSTALLDIR_SBIN);
	[ -d $(INSTALLDIR_ETC) ] || mkdir $(INSTALLDIR_ETC);
	cp urCreator $(INSTALLDIR_LIBEXEC)
	cp urCollector.pl $(INSTALLDIR_SBIN)
	cp urCollector.conf-template $(INSTALLDIR_ETC)
clean : 
	rm -f urCreator
