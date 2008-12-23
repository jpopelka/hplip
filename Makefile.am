#
#  Makefile.am - hplip automake input file
#
#  (c) 2004-2007 Copyright Hewlett-Packard Development Company, LP
#

INCLUDES = -Iip -Iio/hpmud -Iscan/sane 

hplipdir = $(datadir)/hplip

docdir = $(hpdocdir)
doc_DATA = COPYING prnt/hpijs/README_LIBJPG
EXTRA_DIST = prnt/hpijs/gdevijs-krgb-1.5-gs8.61.patch prnt/hpijs/README_LIBJPG

dist_noinst_SCRIPTS = 
dist_noinst_DATA =
noinst_PROGRAMS =
lib_LTLIBRARIES = 

include foomatic_drv.inc
include unreleased.inc

if DOC_BUILD
wwwsrc = doc
www0dir = $(docdir)
dist_www0_DATA = $(wwwsrc)/index.html $(wwwsrc)/commandline.html $(wwwsrc)/copying.html $(wwwsrc)/devicemanager.html $(wwwsrc)/faxtrouble.html $(wwwsrc)/gettinghelp.html $(wwwsrc)/hpscan.html $(wwwsrc)/mainttask.html $(wwwsrc)/plugins.html $(wwwsrc)/print.html $(wwwsrc)/printing.html $(wwwsrc)/printoptions.html $(wwwsrc)/printtroubleshooting.html $(wwwsrc)/scanning.html $(wwwsrc)/scantrouble.html $(wwwsrc)/sendfax.html $(wwwsrc)/setup.html $(wwwsrc)/systray.html $(wwwsrc)/troubleshooting.html $(wwwsrc)/uninstalling.html $(wwwsrc)/upgrading.html
www3dir = $(docdir)/styles
dist_www3_DATA = $(wwwsrc)/styles/*
www4dir = $(docdir)/images
dist_www4_DATA = $(wwwsrc)/images/*
endif

if HPLIP_BUILD

dist_hplip_SCRIPTS = hpssd.py __init__.py hpdio.py
dist_noinst_DATA += scan/sane/hpaio.desc prnt/drv/hpijs.drv.in.template
dist_noinst_SCRIPTS += dat2drv.py install.py hplip-install

cmddir = $(hplipdir)
dist_cmd_SCRIPTS = align.py info.py print.py toolbox.py clean.py colorcal.py unload.py testpage.py makeuri.py check.py fab.py levels.py \
	sendfax.py setup.py makecopies.py probe.py timedate.py firmware.py scan.py systray.py plugin.py linefeedcal.py pqdiag.py \
	faxsetup.py devicesetup.py printsettings.py

# hp backend.
hpdir = $(cupsbackenddir)
hp_PROGRAMS = hp
hp_SOURCES = prnt/backend/hp.c
hp_LDADD = libhpmud.la $(DBUS_LIBS)
hp_CFLAGS = $(DBUS_CFLAGS)

# hp-mkuri.
hp_mkuridir = $(bindir)
hp_mkuri_PROGRAMS = hp-mkuri
hp_mkuri_SOURCES = io/hpmud/hp-mkuri.c
hp_mkuri_LDADD = libhpmud.la

# base
basedir = $(hplipdir)/base

dist_base_SCRIPTS = base/maint.py base/codes.py base/g.py base/pml.py base/status.py  \
	base/__init__.py base/mfpdtf.py base/utils.py \
	base/device.py base/logger.py base/slp.py base/exif.py base/strings.py base/magic.py \
	base/imagesize.py base/pexpect.py base/models.py base/mdns.py base/tui.py base/dime.py \
	base/ldif.py base/vcard.py base/module.py

# installer
installdir = $(hplipdir)/installer
dist_install_SCRIPTS = installer/__init__.py installer/dcheck.py installer/distros.dat installer/core_install.py
dist_noinst_SCRIPTS += installer/text_install.py

# installer/web_install.py installer/trigger.py  installer/fix_symlink.py
#dist_noinst_SCRIPTS += installer/pages/__init__.py installer/pages/install_required.tmpl installer/pages/installation_path.tmpl 
#installer/pages/component.tmpl \
#	installer/pages/mode.tmpl installer/pages/confirm_distro.tmpl installer/pages/notes.tmpl installer/pages/error.tmpl 
#installer/pages/options.tmpl \
#	installer/pages/error_package_manager.tmpl installer/pages/password.tmpl installer/pages/error_required_missing.tmpl 
#installer/pages/progress.tmpl \
#	installer/pages/error_unsupported_distro.tmpl installer/pages/ready_to_build.tmpl installer/pages/finished.tmpl 
#installer/pages/select_distro.tmpl \
#	installer/pages/hplip_remove.tmpl installer/pages/hpoj_remove.tmpl installer/pages/unsupported.tmpl installer/pages/turn_off_options.tmpl \
#	installer/pages/index.tmpl installer/pages/welcome.tmpl installer/pages/install_optional.tmpl installer/pages/quit.tmpl \
#	installer/pages/install_required.tmpl installer/pages/replug.tmpl installer/pages/restart.tmpl installer/pages/network_unavailable.tmpl \
#	installer/pages/warning.tmpl
#dist_noinst_SCRIPTS += installer/scripts/hplip.js installer/scripts/encode.js installer/scripts/misc_code.js
#dist_noinst_DATA += installer/images/button.png installer/images/favicon.ico installer/images/topbar.png installer/images/view.png \
#	installer/images/back.png installer/images/circular.gif installer/images/hplogo.png installer/images/tux.png \
#	installer/images/button1.png installer/images/button1d.png installer/images/replug1.png installer/images/replug2.png \
#	installer/images/replug3.png installer/images/button2.png
#dist_noinst_DATA += installer/localization/gui_strings_de_DE.ts installer/localization/gui_strings_en_US.ts 
#installer/localization/gui_strings_es_MX.ts \
#	installer/localization/gui_strings_fr_FR.ts installer/localization/gui_strings_it_IT.ts installer/localization/gui_strings_pt_BR.ts \
#	installer/localization/gui_strings_ru_RU.ts installer/localization/gui_strings_zh_CN.ts

#dist_noinst_SCRIPTS += installer/styles/hplip.css installer/styles/misc.css

# makecopies
copierdir = $(hplipdir)/copier
dist_copier_SCRIPTS = copier/copier.py copier/__init__.py

# fax
if FAX_BUILD
faxdir = $(hplipdir)/fax
dist_fax_SCRIPTS = fax/fax.py fax/__init__.py fax/coverpages.py fax/pmlfax.py fax/soapfax.py fax/faxdevice.py
hpfaxdir = $(cupsbackenddir)
dist_hpfax_SCRIPTS = fax/backend/hpfax.py
faxppddir = $(hpppddir)
dist_faxppd_DATA = fax/ppd/HP-Fax-hplip.ppd.gz fax/ppd/HP-Fax2-hplip.ppd.gz
endif

# ptest
noinst_PROGRAMS += ptest
ptest_SOURCES = pcard/ptest.c pcard/ptest.h pcard/fat.c pcard/fat.h 
ptest_LDADD = libhpmud.la

# data
modelsdir = $(hplipdir)/data/models
images_16x16dir = $(hplipdir)/data/images/16x16
images_24x24dir = $(hplipdir)/data/images/24x24
images_32x32dir = $(hplipdir)/data/images/32x32
images_48x48dir = $(hplipdir)/data/images/48x48
images_128x128dir = $(hplipdir)/data/images/128x128
images_devicesdir = $(hplipdir)/data/images/devices
images_otherdir = $(hplipdir)/data/images/other
pcldir = $(hplipdir)/data/pcl
ldldir = $(hplipdir)/data/ldl
postscriptdir = $(hplipdir)/data/ps
localzdir = $(hplipdir)/data/localization
dist_postscript_DATA = data/ps/testpage.ps.gz data/ps/clean_page.pdf.gz
dist_models_DATA = data/models/models.dat

if GUI_BUILD
dist_images_16x16_DATA = data/images/16x16/*
dist_images_24x24_DATA = data/images/24x24/*
dist_images_32x32_DATA = data/images/32x32/*
dist_images_48x48_DATA = data/images/48x48/*
dist_images_128x128_DATA = data/images/128x128/*
dist_images_devices_DATA = data/images/devices/*
dist_images_other_DATA = data/images/other/*
endif

dist_pcl_DATA = data/pcl/align1_8xx.pcl.gz data/pcl/align1_9xx.pcl.gz data/pcl/align2_8xx.pcl.gz data/pcl/align3_8xx.pcl.gz data/pcl/align4_8xx.pcl.gz \
	data/pcl/align5_8xx.pcl.gz data/pcl/align2_9xx.pcl.gz data/pcl/align3_9xx.pcl.gz data/pcl/align4_450.pcl.gz data/pcl/align6_450.pcl.gz \
	data/pcl/colorcal1_450.pcl.gz data/pcl/colorcal2_450.pcl.gz data/pcl/crbcal.pcl.gz data/pcl/crcaldone.pcl.gz data/pcl/crcbcal.pcl.gz data/pcl/crccal.pcl.gz \
	data/pcl/crcpcal.pcl.gz data/pcl/crpcal.pcl.gz 
dist_ldl_DATA = data/ldl/cb2pcal.ldl.gz data/ldl/cb2pcal_done.ldl.gz data/ldl/cbbcal.ldl.gz data/ldl/cbccal.ldl.gz data/ldl/cbccal_done.ldl.gz data/ldl/cbcpcal.ldl.gz \
	data/ldl/cbpcal.ldl.gz
dist_localz_DATA = data/localization/hplip_de.qm data/localization/hplip_es.qm data/localization/hplip_fr.qm data/localization/hplip_it.qm \
	data/localization/hplip_pt.qm data/localization/hplip_ru.qm data/localization/hplip_zh.qm
dist_noinst_DATA += data/localization/hplip_de.ts data/localization/hplip_es.ts data/localization/hplip_fr.ts data/localization/hplip_it.ts \
	data/localization/hplip_pt.ts data/localization/hplip_ru.ts data/localization/hplip_zh.ts

# pcard 
pcarddir = $(hplipdir)/pcard
dist_pcard_SCRIPTS = pcard/__init__.py pcard/photocard.py

# pcardext
pcardextdir = $(pyexecdir)
pcardext_LTLIBRARIES = pcardext.la
pcardext_la_LDFLAGS = -module -avoid-version
pcardext_la_SOURCES = pcard/pcardext/pcardext.c pcard/fat.c
pcardext_la_CFLAGS = -I$(PYTHONINCLUDEDIR)

# prnt
prntdir = $(hplipdir)/prnt
dist_prnt_SCRIPTS = prnt/cups.py prnt/__init__.py prnt/ldl.py prnt/pcl.py prnt/colorcal.py

# cupsext
cupsextdir = $(pyexecdir)
cupsext_LTLIBRARIES = cupsext.la
cupsext_la_LDFLAGS = -module -avoid-version
cupsext_la_SOURCES =  prnt/cupsext/cupsext.c 
cupsext_la_CFLAGS = -I$(PYTHONINCLUDEDIR)
cupsext_la_LIBADD = -lcups

# ip library
lib_LTLIBRARIES += libhpip.la
libhpip_la_LDFLAGS = -lm -version-info 0:1:0
libhpip_la_SOURCES = ip/xconvolve.c ip/xfax.c ip/xgrayout.c ip/xjpg_dct.c ip/xjpg_fix.c ip/xpad.c ip/xrotate.c ip/xskel.c ip/xtiff.c \
	ip/ipmain.c ip/xchgbpp.c ip/xcrop.c ip/xgamma.c ip/xjpg_dec.c ip/xjpg_huf.c ip/xpcx.c ip/xsaturation.c ip/xtable.c ip/xtonemap.c \
	ip/xbi2gray.c ip/xcolrspc.c ip/xfakemono.c ip/xgray2bi.c ip/xinvert.c ip/xjpg_enc.c ip/xmatrix.c ip/xpnm.c ip/xscale.c ip/xthumb.c ip/xyxtract.c \
	ip/hpip.h ip/ipdefs.h ip/xform.h ip/xjpg_dct.h ip/xjpg_huf.h ip/xjpg_mrk.h 

# hpaio sane backend
if SCAN_BUILD
libsane_hpaiodir = $(libdir)/sane
libsane_hpaio_LTLIBRARIES = libsane-hpaio.la
libsane_hpaio_la_SOURCES = scan/sane/hpaio.c scan/sane/mfpdtf.c scan/sane/pml.c scan/sane/scl.c scan/sane/io.c scan/sane/hpaio.h \
	  scan/sane/pml.h scan/sane/saneopts.h scan/sane/io.h scan/sane/mfpdtf.h scan/sane/sane.h scan/sane/scl.h scan/sane/tables.h \
	  scan/sane/common.c scan/sane/common.h scan/sane/soap.h scan/sane/soapht.h scan/sane/sanei_debug.h scan/sane/sanei.h \
	  scan/sane/sanei_init_debug.c scan/sane/marvell.h scan/sane/marvelli.h scan/sane/marvell.c scan/sane/soapht.c scan/sane/soap.c \
          scan/sane/soaphti.h scan/sane/soapi.h scan/sane/xml.c scan/sane/xml.h 
if DARWIN_BUILD
libsane_hpaio_la_LDFLAGS = -module -framework CoreFoundation -version-info 1:0:0
else
libsane_hpaio_la_LDFLAGS = -version-info 1:0:0
endif
# The following is a interlibrary dependency that must be compiled first.
libsane_hpaio_la_LIBADD = libhpip.la libhpmud.la $(DBUS_LIBS) -lcups
#libsane_hpaio_la_CFLAGS = -DWITH_NONAMESPACES -DSOAP_DEBUG
libsane_hpaio_la_CFLAGS = $(DBUS_CFLAGS) 

# scan
scandir = $(hplipdir)/scan
dist_scan_SCRIPTS = scan/__init__.py scan/sane.py

# scanext
scanextdir = $(pyexecdir)
scanext_LTLIBRARIES = scanext.la
scanext_la_LDFLAGS = -module -avoid-version -lsane
scanext_la_SOURCES =  scan/scanext/scanext.c 
scanext_la_CFLAGS = -I$(PYTHONINCLUDEDIR)
endif

# hpmud library
MUDNAME=hpmud
lib_LTLIBRARIES += libhpmud.la
libhpmud_la_SOURCES = io/hpmud/hpmud.c io/hpmud/mlc.c io/hpmud/model.c io/hpmud/musb.c io/hpmud/pml.c \
	  io/hpmud/hpmud.h io/hpmud/hpmudi.h io/hpmud/list.h io/hpmud/mlc.h io/hpmud/musb.h io/hpmud/pml.h io/hpmud/dot4.c \
	  io/hpmud/dot4.h io/hpmud/jd.c io/hpmud/jd.h io/hpmud/pp.c io/hpmud/pp.h 
if NETWORK_BUILD
libhpmud_la_LDFLAGS = -version-info 0:4:0 -lusb -lpthread -lnetsnmp -lcrypto
else
libhpmud_la_LDFLAGS = -version-info 0:4:0 -lusb -lpthread
endif
libhpmud_la_CFLAGS = -DMUDNAME=\"$(MUDNAME)\" -DCONFDIR=\"$(hplip_confdir)\"

# hpmudext
hpmudextdir = $(pyexecdir)
hpmudext_LTLIBRARIES = hpmudext.la
hpmudext_la_LDFLAGS = -module -avoid-version
hpmudext_la_SOURCES = io/mudext/hpmudext.c
hpmudext_la_LIBADD = libhpmud.la
hpmudext_la_CFLAGS = -I$(PYTHONINCLUDEDIR)

# hpmud.rules
rulesdir = /etc/udev/rules.d
dist_rules_DATA = data/rules/55-hpmud.rules
halpredir = /usr/share/hal/fdi/preprobe/10osvendor
dist_halpre_DATA = data/rules/20-hplip-devices.fdi

# ui (qt3)
if GUI_BUILD
if QT3_INSTALL
uidir = $(hplipdir)/ui
dist_ui_SCRIPTS = ui/alignform.py \
	ui/colorcalform_base.py ui/colorcalform.py ui/coloradjform_base.py ui/coloradjform.py ui/devmgr4_base.py ui/devmgr4.py \
	ui/__init__.py ui/loadpaperform_base.py ui/loadpaperform.py \
	ui/paperedgealignform_base.py ui/paperedgealignform.py ui/ui_utils.py \
	ui/settingsdialog_base.py ui/settingsdialog.py ui/aligntype6form1.py ui/aligntype6form1_base.py ui/aligntype6form2_base.py \
	ui/aligntype6form2.py ui/nodevicesform_base.py ui/nodevicesform.py ui/unloadform.py \
	ui/imagepropertiesdlg_base.py ui/imagepropertiesdlg.py ui/choosedevicedlg.py ui/chooseprinterdlg.py \
	ui/aboutdlg.py ui/aboutdlg_base.py ui/waitform.py ui/waitform_base.py ui/cleaningform_base.py ui/cleaningform.py \
	ui/cleaningform2_base.py ui/cleaningform2.py ui/colorcalform2_base.py ui/colorcalform2.py ui/colorcal4form.py \
	ui/colorcal4form_base.py ui/colorcal4form_base.ui ui/printerform.py \
	ui/faxaddrbookgroupsform_base.py ui/faxaddrbookgroupeditform_base.py ui/faxaddrbookform_base.py \
	ui/faxaddrbookform.py ui/faxaddrbookeditform_base.py ui/align10form.py ui/align10form_base.py \
	ui/faxsendjobform.py ui/faxsettingsform_base.py ui/faxsettingsform.py \
	ui/coverpageform_base.py ui/coverpageform.py ui/allowabletypesdlg_base.py ui/allowabletypesdlg.py \
	ui/makecopiesform.py ui/setupform_base.py ui/setupform.py ui/setupmanualfind_base.py \
	ui/setupmanualfind.py ui/setupsettings_base.py ui/setupsettings.py ui/scrollview.py \
	ui/scrollprintsettings.py ui/scrollprint.py ui/scrollfax.py \
	ui/scrollunload.py ui/scrollcopy.py ui/pluginform2.py ui/pluginform2_base.py ui/systemtray.py \
	ui/ui_utils.py ui/jobstoragemixin.py ui/pluginlicenseform_base.py ui/pluginlicenseform.py \
	ui/align13form_base.py ui/align13form.py

dist_noinst_DATA += ui/colorcalform2_base.ui ui/settingsdialog_base.ui ui/aligntype6form1_base.ui \
	ui/aboutdlg_base.ui ui/imagepropertiesdlg_base.ui ui/paperedgealignform_base.ui ui/aligntype6form2_base.ui \
	ui/nodevicesform_base.ui ui/cleaningform_base.ui ui/colorcalform_base.ui ui/devmgr4_base.ui ui/loadpaperform_base.ui \
	ui/cleaningform2_base.ui ui/waitform_base.ui ui/coloradjform_base.ui ui/faxaddrbookeditform_base.ui \
	ui/faxaddrbookform_base.ui ui/faxaddrbookgroupeditform_base.ui ui/faxaddrbookgroupsform_base.ui \
	ui/align10form_base.ui  ui/pluginform2_base.ui \
	plugins/powersettingsdialog_base.ui ui/faxsettingsform_base.ui ui/coverpageform_base.ui \
	ui/allowabletypesdlg_base.ui ui/setupform_base.ui ui/setupmanualfind_base.ui \
	ui/setupsettings_base.ui ui/pluginlicenseform_base.ui ui/align13form_base.ui
endif
endif

#ui4 (qt4)
if GUI_BUILD
if QT4_INSTALL
ui4dir=$(hplipdir)/ui4
#dist_ui4_SCRIPTS = ui4/devmgr5.py ui4/systemtray.py ui4/devmgr5_base.py ui4/__init__.py ui4/ui_utils.py \
#	ui4/settingsdialog_base.py ui4/settingsdialog.py ui4/printsettingstoolbox.py ui4/printdialog_base.py \
#	ui4/printdialog.py
#dist_noinst_DATA += ui4/devmgr5_base.ui ui4/settingsdialog_base.ui ui4/printdialog_base.ui
dist_ui4_SCRIPTS = ui4/*.py
dist_noinst_DATA += ui4/*.ui
endif
endif

# ui plugins (qt3)
if GUI_BUILD
if QT3_INSTALL
pluginsdir = $(hplipdir)/plugins
dist_plugins_SCRIPTS = plugins/dj450.py plugins/__init__.py plugins/powersettings.py plugins/powersettingsdialog.py \
	plugins/powersettingsdialog_base.py plugins/Deskjet_460.py plugins/Officejet_H470.py plugins/powersettings2.py
endif
endif

# ui plugins (qt4)
if GUI_BUILD
if QT4_INSTALL
plugins4dir = $(hplipdir)/ui4/plugins
dist_plugins4_SCRIPTS =
endif
endif


# cheetah
#dist_noinst_SCRIPTS += Cheetah/Filters.py Cheetah/SettingsManager.py Cheetah/CheetahWrapper.py Cheetah/ImportHooks.py \
#	Cheetah/SourceReader.py Cheetah/Compiler.py Cheetah/ImportManager.py Cheetah/Template.py Cheetah/DummyTransaction.py \
#	Cheetah/NameMapper.py Cheetah/TemplateCmdLineIface.py Cheetah/ErrorCatchers.py Cheetah/Parser.py Cheetah/Version.py \
#	Cheetah/FileUtils.py Cheetah/Servlet.py Cheetah/CacheRegion.py Cheetah/__init__.py
#dist_noinst_SCRIPTS += Cheetah/Utils/Indenter.py Cheetah/Utils/Misc.py Cheetah/Utils/VerifyType.py \
#	Cheetah/Utils/WebInputMixin.py Cheetah/Utils/__init__.py
#dist_noinst_SCRIPTS += Cheetah/Utils/optik/errors.py Cheetah/Utils/optik/option_parser.py Cheetah/Utils/optik/option.py \
#	Cheetah/Utils/optik/__init__.py

# cherrypy
#dist_noinst_SCRIPTS += cherrypy/_cphttptools.py cherrypy/_cpwsgi.py cherrypy/__init__.py cherrypy/_cpserver.py cherrypy/_cpwsgiserver.py \
#	cherrypy/_cpcgifs.py cherrypy/_cpthreadinglocal.py cherrypy/config.py cherrypy/_cpengine.py cherrypy/_cptree.py cherrypy/_cperror.py \
#	cherrypy/_cputil.py 
#dist_noinst_SCRIPTS += cherrypy/lib/covercp.py cherrypy/lib/form.py cherrypy/lib/__init__.py cherrypy/lib/cptools.py \
#	cherrypy/lib/httptools.py cherrypy/lib/autoreload.py cherrypy/lib/defaultformmask.py cherrypy/lib/profiler.py
#dist_noinst_SCRIPTS += cherrypy/filters/nsgmlsfilter.py cherrypy/filters/__init__.py \
#	cherrypy/filters/responseheadersfilter.py \
#	cherrypy/filters/basefilter.py cherrypy/filters/sessionauthenticatefilter.py cherrypy/filters/baseurlfilter.py \
#	cherrypy/filters/sessionfilter.py cherrypy/filters/cachefilter.py cherrypy/filters/staticfilter.py \
#	cherrypy/filters/decodingfilter.py cherrypy/filters/tidyfilter.py cherrypy/filters/encodingfilter.py \
#	cherrypy/filters/virtualhostfilter.py cherrypy/filters/gzipfilter.py cherrypy/filters/wsgiappfilter.py \
#	cherrypy/filters/logdebuginfofilter.py cherrypy/filters/xmlrpcfilter.py

# hppgsz
noinst_PROGRAMS += hppgsz
hppgsz_SOURCES = $(apdk_SOURCES) prnt/hpijs/PrinterProperties.cpp prnt/hpijs/PrinterProperties.h
hppgsz_CXXFLAGS = $(hpijs_CXXFLAGS)
#hppgsz_CFLAGS = $(hpijs_CXXFLAGS) -Iprnt/hpijs
hppgsz_CFLAGS = $(hpijs_CFLAGS)
hppgsz_LDADD = $(hpijs_LDADD)

# hplip.desktop
hplip_desktopdir = $(icondir)
hplip_desktop_DATA = hplip.desktop

# hplip.conf
hplip_confdir = /etc/hp
hplip_conf_DATA = hplip.conf

# hplip-systray.desktop
hplip_systraydir = $(systraydir)
hplip_systray_DATA = hplip-systray.desktop

# hpipjs (CUPS filter)
hplipjsdir = $(cupsfilterdir)
hplipjs_PROGRAMS = hplipjs
hplipjs_SOURCES = prnt/filters/hplipjs.c

endif	# if HPLIP_BUILD

# foomatic-rip-hplip
if RIP_INSTALL
ripdir = $(cupsfilterdir)
dist_rip_SCRIPTS = prnt/hpijs/foomatic-rip-hplip
endif

# hpijs
bin_PROGRAMS = hpijs
apdk_SOURCES = prnt/hpijs/models.cpp prnt/hpijs/breaks_open.cpp \
	prnt/hpijs/dj9xxvip.cpp prnt/hpijs/dj9xx.cpp prnt/hpijs/capture.cpp prnt/hpijs/colormatch.cpp prnt/hpijs/colormatcher_open.cpp \
	prnt/hpijs/compression.cpp prnt/hpijs/context.cpp prnt/hpijs/create_so.cpp prnt/hpijs/creator.cpp \
	prnt/hpijs/dj600.cpp prnt/hpijs/dj630.cpp prnt/hpijs/dj660.cpp prnt/hpijs/dj690.cpp prnt/hpijs/dj6xx.cpp prnt/hpijs/dj8xx.cpp prnt/hpijs/dj600_maps.cpp \
	prnt/hpijs/dj660_maps.cpp prnt/hpijs/dj690_maps.cpp prnt/hpijs/dj895_maps.cpp prnt/hpijs/dj895_maps2.cpp prnt/hpijs/dj970_maps.cpp \
	prnt/hpijs/dj970_maps2.cpp prnt/hpijs/dj970_maps3.cpp prnt/hpijs/filterhpa.cpp prnt/hpijs/apollo21xx.cpp prnt/hpijs/apollo2560.cpp prnt/hpijs/apollo2xxx.cpp \
	prnt/hpijs/dj8x5.cpp prnt/hpijs/psp100.cpp prnt/hpijs/phobos_cmaps.cpp prnt/hpijs/dj350.cpp prnt/hpijs/halftoner.cpp prnt/hpijs/halftoner_open.cpp \
	prnt/hpijs/globals.cpp prnt/hpijs/header.cpp prnt/hpijs/htmtxhi.cpp prnt/hpijs/pmselect.cpp \
	prnt/hpijs/job.cpp prnt/hpijs/printer.cpp prnt/hpijs/registry.cpp prnt/hpijs/scaler.cpp \
	prnt/hpijs/scaler_open.cpp prnt/hpijs/script.cpp prnt/hpijs/systemservices.cpp \
	prnt/hpijs/translator.cpp prnt/hpijs/version.cpp prnt/hpijs/versioncode.cpp \
	prnt/hpijs/djgenericvip.cpp prnt/hpijs/dj540.cpp prnt/hpijs/dj850.cpp prnt/hpijs/dj850_maps.cpp prnt/hpijs/dj890.cpp \
	prnt/hpijs/apollo21xx.h prnt/hpijs/apollo2560.h prnt/hpijs/apollo2xxx.h prnt/hpijs/colormatch.h prnt/hpijs/colormatcher_open.h \
	prnt/hpijs/compression.h prnt/hpijs/config.h prnt/hpijs/context.h prnt/hpijs/dj350.h prnt/hpijs/dj400.h prnt/hpijs/dj540.h \
	prnt/hpijs/dj600.h prnt/hpijs/dj630.h prnt/hpijs/dj660.h prnt/hpijs/dj690.h prnt/hpijs/dj6xx.h prnt/hpijs/dj8x5.h prnt/hpijs/dj8xx.h \
	prnt/hpijs/dj850.h prnt/hpijs/dj890.h prnt/hpijs/dj9xx.h prnt/hpijs/dj9xxvip.h \
	prnt/hpijs/ernieplatform.h prnt/hpijs/filterhpa.h prnt/hpijs/global_types.h prnt/hpijs/halftoner.h prnt/hpijs/font.h prnt/hpijs/debug.h \
	prnt/hpijs/halftoner_open.h prnt/hpijs/header.h prnt/hpijs/hpprint_c_api.h \
	prnt/hpijs/hpprintapi.h prnt/hpijs/hptypes.h prnt/hpijs/htfed.h prnt/hpijs/internal.h \
	prnt/hpijs/interp.h prnt/hpijs/interp_data_50.h prnt/hpijs/io_defs.h prnt/hpijs/job.h prnt/hpijs/models.h prnt/hpijs/modes.h prnt/hpijs/pmselect.h \
	prnt/hpijs/printer.h prnt/hpijs/psp100.h prnt/hpijs/psp470.h prnt/hpijs/resources.h prnt/hpijs/scaler_open.h prnt/hpijs/scaler_prop.h prnt/hpijs/script.h \
	prnt/hpijs/systemservices.h prnt/hpijs/unistd_.h prnt/hpijs/djgenericvip.h prnt/hpijs/ljmono.h prnt/hpijs/ljmono.cpp \
	prnt/hpijs/dj3320.cpp prnt/hpijs/dj3320.h prnt/hpijs/dj3320_cmap.cpp prnt/hpijs/dj3600.cpp prnt/hpijs/dj3600.h prnt/hpijs/dj3600_cmap.cpp prnt/hpijs/dj4100.h \
	prnt/hpijs/dj4100_cmap.cpp prnt/hpijs/ldlencap.h prnt/hpijs/ljcolor.cpp prnt/hpijs/ljcolor.h prnt/hpijs/pscript.h \
	prnt/hpijs/printerproxy.cpp prnt/hpijs/printerfactory.cpp prnt/hpijs/printerproxy.h prnt/hpijs/printerfactory.h \
	prnt/hpijs/ljjetready.cpp prnt/hpijs/ljjetready.h prnt/hpijs/jdatadbf.c prnt/hpijs/jccolor.c prnt/hpijs/ljfastraster.cpp prnt/hpijs/ljfastraster.h \
	prnt/hpijs/jinclude.h prnt/hpijs/jpegint.h prnt/hpijs/dj55xx.h prnt/hpijs/hpijsfax.h prnt/hpijs/ojprokx50.h \
	prnt/hpijs/ljzjs.cpp prnt/hpijs/ljzjs.h prnt/hpijs/ljzjsmono.cpp prnt/hpijs/ljm1005.cpp prnt/hpijs/ljm1005.h \
	prnt/hpijs/ljzjsmono.h prnt/hpijs/hpjbig_wrapper.h prnt/hpijs/quickconnect.cpp prnt/hpijs/quickconnect.h prnt/hpijs/ljp1xxx.h
hpijs_SOURCES = $(apdk_SOURCES) prnt/hpijs/hpijs.cpp prnt/hpijs/ijs_server.c prnt/hpijs/ijs.c prnt/hpijs/hpijsfax.cpp prnt/hpijs/services.cpp \
	prnt/hpijs/hpijs.h prnt/hpijs/ijs.h prnt/hpijs/ijs_server.h prnt/hpijs/services.h prnt/hpijs/ijs_client.h prnt/hpijs/hpiom.c prnt/hpijs/hpiom.h 
hpijs_CXXFLAGS = -DAPDK_DJ660 -DAPDK_DJ6xx -DAPDK_DJ6xxPhoto -DAPDK_DJ8xx -DAPDK_DJ9xx -DAPDK_DJ9xxVIP -DAPDK_DJ630 \
	-DAPDK_APOLLO2XXX -DAPDK_APOLLO21XX -DAPDK_APOLLO2560 -DAPDK_DJ600 -DAPDK_DJ350 -DAPDK_DJ8x5 -DAPDK_PSP100 -DAPDK_AUTODUPLEX \
	-DAPDK_HIGH_RES_MODES -DAPDK_LJMONO -DAPDK_DJ540 -DAPDK_DJ850 -DAPDK_DJ890 -DAPDK_DJ3320 -DAPDK_LJCOLOR -DAPDK_DJGENERICVIP \
	-DAPDK_LJJETREADY  -DAPDK_LJFASTRASTER -DAPDK_BUFFER_SEND -DAPDK_LDL_COMPRESS -DAPDK_EXTENDED_MEDIASIZE \
	-DAPDK_MLC_PRINTER -DAPDK_DJ3600 -DAPDK_LJZJS_MONO -DAPDK_LJM1005 -DAPDK_QUICKCONNECT \
                $(APDK_ENDIAN_FLAG) $(APDK_AUTO_INCLUDE_FLAG) -DAPDK_LINUX -DNDEBUG $(DBUS_CFLAGS)
hpijs_CFLAGS = $(hpijs_CXXFLAGS) -Iprnt/hpijs 

if HPLIP_BUILD
hpijs_LDADD = -ljpeg -ldl libhpip.la libhpmud.la $(DBUS_LIBS)
else
hpijs_LDADD = -ljpeg -ldl
endif

# PPDs
ppddir = $(hpppddir)
dist_ppd_DATA = $(foomatic_ps_printers)
if FOOMATIC_PPD_INSTALL
dist_ppd_DATA += $(foomatic_ppd_printers)
endif
if FOOMATIC_DRV_INSTALL
cupsdrvdir = $(drvdir)
dist_cupsdrv_DATA = $(foomatic_drv)
endif

install-data-hook: 
if HPLIP_BUILD
#	   If scanner build, add hpaio entry to sane dll.conf.
	if [ "$(scan_build)" = "yes" ]; then \
	   $(mkinstalldirs) $(DESTDIR)/etc/sane.d; \
	   if [ ! -f $(DESTDIR)/etc/sane.d/dll.conf ]; then \
		  touch $(DESTDIR)/etc/sane.d/dll.conf; \
	   fi; \
	   if ! grep ^hpaio $(DESTDIR)/etc/sane.d/dll.conf >/dev/null 2>/dev/null ; then \
		  echo "Adding hpaio entry to /etc/sane.d/dll.conf." ; \
		  echo hpaio >>$(DESTDIR)/etc/sane.d/dll.conf ; \
	   fi \
	fi
#	   Create hp-xxx commands in bindir.
	$(mkinstalldirs) $(DESTDIR)$(bindir)
	for i in $(dist_cmd_SCRIPTS); do \
	   cmd=`basename $$i .py`; \
	   if [ ! \( "$$cmd" = "toolbox" -a "$(gui_build)" = "no" \) ]; then \
		  ln -sf ../share/$(PACKAGE)/$$i $(DESTDIR)$(bindir)/hp-$$cmd; \
	   fi \
	done
#
#	   Install fax support. 
	if [ "$(fax_build)" = "yes" ]; then \
	   mv $(DESTDIR)$(hpfaxdir)/hpfax.py $(DESTDIR)$(hpfaxdir)/hpfax; \
	   chmod 700 $(DESTDIR)$(hpfaxdir)/hpfax; \
	fi
#
#       Make backend run as root.
#	chmod 700 $(DESTDIR)$(hpdir)/hp
endif # if HPLIP_BUILD

uninstall-hook: 
if HPLIP_BUILD
#	   Remove hp-xxx commands.
	for i in $(dist_cmd_SCRIPTS); do \
		cmd=`basename $$i .py`; \
		rm -f $(DESTDIR)$(bindir)/hp-$$cmd; \
	done
#
#	   Remove fax support.
	rm -f $(DESTDIR)$(hpfaxdir)/hpfax 
endif

rpm_unleaded:
	epm -f rpm hpliplite UNLEADED=1 hplip.list
rpm_regular:
	epm -f rpm hplipfull hplip.list
deb_unleaded:
	epm -f deb hpliplite UNLEADED=1 hplip.list
deb_regular:
	epm -f deb hplipfull hplip.list
epm_unleaded:
	epm hpliplite UNLEADED=1 hplip.list
epm_regular:
	epm hplipfull hplip.list
