/*****************************************************************************\
    hpcups.cpp : HP cups filter

    Copyright (c) 2009, Hewlett-Packard Co.
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions
    are met:
    1. Redistributions of source code must retain the above copyright
       notice, this list of conditions and the following disclaimer.
    2. Redistributions in binary form must reproduce the above copyright
       notice, this list of conditions and the following disclaimer in the
       documentation and/or other materials provided with the distribution.
    3. Neither the name of the Hewlett-Packard nor the names of its
       contributors may be used to endorse or promote products derived
       from this software without specific prior written permission.

    THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
    IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
    OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
    IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
    INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
    NOT LIMITED TO, PATENT INFRINGEMENT; PROCUREMENT OF SUBSTITUTE GOODS OR
    SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
    HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
    STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
    IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
    POSSIBILITY OF SUCH DAMAGE.
\*****************************************************************************/

#include <sys/stat.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <syslog.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include "header.h"
#include "ijs.h"
#include "ijs_server.h"
#include "hpimage.h"

/*
typedef struct
{
    int    width;
    int    height;
    char   cs[32];
} IjsPageHeader;
*/

#include "services.h"

#include <cups/cups.h>
#include <cups/raster.h>
#include "hpcups.h"

void SendDbusMessage (const char *dev, const char *printer, int code, 
                      const char *username, const int jobid, const char *title);

#ifdef HAVE_LIBHPIP
extern  int hpijsFaxServer (int argc, char **argv);
#endif

HPCups::HPCups ()
{
    m_pSys      = NULL;
    m_fd        = 0;
    m_iLogLevel = 0;
}

HPCups::~HPCups ()
{
    if (m_fd)
    {
        close (m_fd);
    }
    if (m_pSys)
    {
        if (m_pSys->pJob)
	{
	    delete m_pSys->pJob;
	}
	if (m_pSys->pPC)
	{
	    delete m_pSys->pPC;
	}
	delete m_pSys;
    }
}

void HPCups::setLogLevel ()
{
    FILE    *fp;
    char    str[258];
    char    *p;
    fp = fopen ("/etc/cups/cupsd.conf", "r");
    if (fp == NULL)
        return;
    while (!feof (fp))
    {
        if (!fgets (str, 256, fp))
	{
	    break;
	}
	if ((p = strstr (str, "hpLogLevel")))
	{
	    p += strlen ("hpLogLevel") + 1;
	    m_iLogLevel = atoi (p);
	    break;
	}
    }
    fclose (fp);
}

int HPCups::initPrintJob ()
{
//    MediaSize       msMedia = sizeUSLetter;
    COLORMODE       colormode;
    int r;
    if (m_iLogLevel & ADDITIONAL_LOG)
    {
        printcupsHeader ();
    }

    if (m_cupsHeader.ImagingBoundingBox[0] == 0)
    {
        m_pSys->FullBleed = 1;
    }

/*
 *  cupsRowStep represents colormode
 *  cupsRowCount represents pen type
 *  cupsOutputType represents quality mode
 */

    m_pSys->pPC->SetPenSet ((PEN_TYPE) (m_cupsHeader.cupsRowCount - 1));
    switch (m_cupsHeader.cupsRowStep)
    {
        case 1:
	    colormode = GREY_K;
	    break;
	case 2:
	    colormode = GREY_CMY;
	default:
	    colormode = COLOR;
	    break;
    }
    if ((r = m_pSys->pPC->SelectPrintMode ((QUALITY_MODE) m_cupsHeader.cupsCompression,
                                  (MEDIATYPE) m_cupsHeader.cupsMediaType, colormode)) != NO_ERROR)
    {
       BOOL        bDevText;
       BUG("unable to set Quality=%d, MediaType=%d, ColorMode=%d, err=%d\n", 
                m_cupsHeader.cupsCompression, m_cupsHeader.cupsMediaType, colormode, r);
       m_pSys->pPC->GetPrintModeSettings((QUALITY_MODE &)m_pSys->Quality, (MEDIATYPE &)m_pSys->MediaType, (COLORMODE &)m_pSys->ColorMode, bDevText);
       BUG("following will be used Quality=%d, MediaType=%d, ColorMode=%d, \n", m_pSys->Quality, m_pSys->MediaType, m_pSys->ColorMode);
    }

    m_pSys->pPC->SetMediaSource ((MediaSource) m_cupsHeader.MediaPosition);
    if (m_cupsHeader.Duplex)
    {
        if (m_cupsHeader.Tumble)
            m_pSys->pPC->SelectDuplexPrinting (DUPLEXMODE_TABLET);
	else
            m_pSys->pPC->SelectDuplexPrinting (DUPLEXMODE_BOOK);
    }
    else
    {
        m_pSys->pPC->SelectDuplexPrinting (DUPLEXMODE_NONE);
    }

//    int      xRes = m_cupsHeader.HWResolution[0];
//    int      yRes = m_cupsHeader.HWResolution[1];
    JobAttributes    ja;

    memset (&ja, 0, sizeof (ja));
    ja.media_attributes.fPhysicalWidth   = (float) m_cupsHeader.PageSize[0] / (float) 72.0;
    ja.media_attributes.fPhysicalHeight  = (float) m_cupsHeader.PageSize[1] / (float) 72.0;
    ja.media_attributes.fPrintableWidth  = (float) (m_cupsHeader.ImagingBoundingBox[2] -
                                   m_cupsHeader.ImagingBoundingBox[0]) / (float) 72.0;
    ja.media_attributes.fPrintableHeight = (float) (m_cupsHeader.ImagingBoundingBox[3] -
                                   m_cupsHeader.ImagingBoundingBox[1]) / (float) 72.0;
    ja.media_attributes.fPrintableStartX = (float) m_cupsHeader.ImagingBoundingBox[0] / (float) 72.0;
    ja.media_attributes.fPrintableStartY = (float) m_cupsHeader.ImagingBoundingBox[1] / (float) 72.0;
    m_pSys->MapPaperSize (ja.media_attributes.fPhysicalWidth, ja.media_attributes.fPhysicalHeight);

    m_pSys->pPC->SetPixelsPerRow (m_cupsHeader.cupsWidth, m_cupsHeader.cupsWidth);

//  Now set all the printer hints
    if (m_cupsHeader.cupsInteger[0])
    {
        // Papersize as PCL id
	ja.media_attributes.pcl_id = m_cupsHeader.cupsInteger[0];
    }
    m_pSys->pPC->SetJobAttributes (&ja);

    PRINTER_HINT    eHint;
    int             iValue;
    for (int i = 1; i < 6; i++)
    {
        eHint = (PRINTER_HINT) i;
	iValue = m_cupsHeader.cupsInteger[i];
	if (iValue)
        {
	    m_pSys->pPC->SetPrinterHint (eHint, iValue);
        }
    }

    // Turn off bi-di support.
    m_pSys->ResetIOMode (FALSE, FALSE);

    // Create a new Job object
    m_pSys->pJob = new Job (m_pSys->pPC);
    if (m_pSys->pJob->constructor_error != NO_ERROR)
    {
        BUG ("ERROR: Unable to create Job object, error = %d\n",
	        m_pSys->pJob->constructor_error);
	return 1;
    }
    return 0;
}

int HPCups::ProcessJob (int argc, char **argv)
{
    int              iStatus = 0;
    cups_raster_t    *cups_raster;

    setLogLevel ();

//  Check commandline.

    if (argc < 6 || argc > 7)
    {
        BUG ("ERROR: %s job-id user title copies options [file]\n", *argv);
	return JOB_CANCELED;
    }

    if (initServices (argv[1]) != 0)
    {
        return 1;
    }
    if (initContext (argv) != 0)
    {
        return 1;
    }

//  Open input stream if it is not stdin
    if (argc == 7)
    {
        m_fd = open (argv[6], O_RDONLY);
	if (m_fd == -1)
	{
	    BUG ("ERROR: Unable to open raster file %s: %m\n", argv[6]);
	    return 1;
	}
    }

    cups_raster = cupsRasterOpen (m_fd, CUPS_RASTER_READ);
    if (cups_raster == NULL)
    {
	BUG ("cupsRasterOpen failed, fd = %d: %m\n", m_fd);
	return 1;
    }

    iStatus = processRasterData (cups_raster);
    cupsRasterClose (cups_raster);

    return iStatus;
}

int HPCups::initServices (char *szJobId)
{
    m_pSys = new UXServices ();
    if (m_pSys->constructor_error != NO_ERROR)
    {
        BUG ("Services object failed, error = %d\n", m_pSys->constructor_error);
	return 1;
    }
    m_pSys->OutputPath = STDOUT_FILENO;
    m_pSys->m_iLogLevel = m_iLogLevel;

//  Does the user wish to send printer ready data to a disk file
    if (m_iLogLevel & SAVE_PCL_FILE)
    {
        char    szFileName[32];
	sprintf (szFileName, "/tmp/hpcups_%s.out", szJobId);
	m_pSys->outfp = fopen (szFileName, "w");
	if (m_pSys->outfp)
	{
	    chmod (szFileName, S_IRUSR | S_IWUSR | S_IRGRP | S_IROTH);
	}
    }

    return 0;
}

int HPCups::initContext (char **argv)
{
    DRIVER_ERROR     err = NO_ERROR;
    ppd_file_t       *ppd;
    ppd_attr_t       *attr;

    m_pSys->pPC = new PrintContext (m_pSys, 0, 0);

/*
 *  If bi-di fails, we still want to continue, so ignore this error.
 *  The failure can also be because of missing plugin. If this printer
 *  requires the plugin, it will be handled later, but if it is optional
 *  then we want to continue.
 */

    if (m_pSys->pPC->constructor_error > 0 &&
        m_pSys->pPC->constructor_error != PLUGIN_LIBRARY_MISSING &&
        m_pSys->DisplayStatus != DISPLAY_PRINTING_CANCELED)
    {
	BUG("PrintContext creation failed, error = %d", m_pSys->pPC->constructor_error);
	return 1;
    }

/*
 *  Check for any warnings, but ignore printmode mismatch warning.
 *  This will happen on monochrome printers. We will select the proper
 *  printmode later.
 */

    if (m_pSys->pPC->constructor_error < 0 &&
        m_pSys->pPC->constructor_error != WARN_MODE_MISMATCH)
    {
        BUG ("WARNING: %s\n", m_pSys->GetDriverMessage (m_pSys->pPC->constructor_error));
	switch (m_pSys->pPC->constructor_error)
	{
	    case WARN_LOW_INK_BOTH_PENS:
	    case WARN_LOW_INK_BLACK:
	    case WARN_LOW_INK_COLOR:
	    case WARN_LOW_INK_PHOTO:
	    case WARN_LOW_INK_GREY:
	    case WARN_LOW_INK_BLACK_PHOTO:
	    case WARN_LOW_INK_COLOR_PHOTO:
	    case WARN_LOW_INK_GREY_PHOTO:
	    case WARN_LOW_INK_COLOR_GREY:
	    case WARN_LOW_INK_COLOR_GREY_PHOTO:
	    case WARN_LOW_INK_COLOR_BLACK_PHOTO:
	    case WARN_LOW_INK_CYAN:
	    case WARN_LOW_INK_MAGENTA:
	    case WARN_LOW_INK_YELLOW:
	    case WARN_LOW_INK_MULTIPLE_PENS:
	    {
	       BUG ("STATE: marker-supply-low-warning\n");
	       break;
	    }
	    default:
	       BUG ("STATE: -marker-supply-low-warning");
	}
    }

//  Select the device class
    ppd = ppdOpenFile (getenv ("PPD"));
    if (ppd == NULL)
    {
        BUG ("ERROR: Unable to open ppd file %s\n", getenv ("PPD"));
	return 1;
    }
    if ((attr = ppdFindAttr (ppd, "cupsModelName", NULL)) == NULL ||
        (attr && attr->value == NULL))
    {
        BUG ("ERROR: Required cupsModelName is missing in ppd file\n");
	ppdClose (ppd);
	return 1;
    }
    err = m_pSys->pPC->SelectDevice (attr->value);
    if (err == PLUGIN_LIBRARY_MISSING)
    {
        // call dbus here
	SendDbusMessage (getenv ("DEVICE_URI"), getenv ("PRINTER"),
	                 EVENT_PRINT_FAILED_MISSING_PLUGIN,
			 argv[2], atoi (argv[1]), argv[3]);
	BUG ("ERROR: unable to set device = %s, err = %d\n", attr->value, err);
	return 1;
    }
    return 0;
}

int HPCups::processRasterData (cups_raster_t *cups_raster)
{
    DRIVER_ERROR           err = NO_ERROR;
    int                    iStatus = 0;
//    int                    iWidthBytes;
    FILE                   *kfp = NULL;
    FILE                   *cfp = NULL;
    int                    iPageNum = 0;
    BYTE                   *black_raster;
    BYTE                   *color_raster;
    BYTE                   *pKRGBRaster;
    BYTE                   *kRaster = NULL;
    BYTE                   *rgbRaster = NULL;
    HPImage                bitmap;
    while (cupsRasterReadHeader2 (cups_raster, &m_cupsHeader))
    {
	iPageNum++;
        if (iPageNum == 1)
	{
	    pKRGBRaster = new BYTE[m_cupsHeader.cupsBytesPerLine];
	    iStatus = initPrintJob ();
	    if (iStatus != 0)
	    {
	        break;
	    }
            if (m_cupsHeader.cupsColorSpace == CUPS_CSPACE_RGBW)
	    {
	        kRaster   = new BYTE[m_cupsHeader.cupsWidth];
	        rgbRaster = new BYTE[m_cupsHeader.cupsWidth * 3];
	        if (kRaster == NULL || rgbRaster == NULL)
	        {
		    BUG ("Memory allocation error\n");
		    iStatus = 1;
	            break;
	        }
	        memset (kRaster, 0, m_cupsHeader.cupsWidth);
	        memset (rgbRaster, 0xFF, m_cupsHeader.cupsWidth * 3);
	    }
	    else if (m_cupsHeader.cupsColorSpace == CUPS_CSPACE_K)
	    {
	        kRaster = pKRGBRaster;
		rgbRaster = NULL;
	    }
	}
	if (m_cupsHeader.cupsColorSpace == CUPS_CSPACE_K)
	{
	    kRaster = pKRGBRaster;
	    rgbRaster = NULL;
	}
	else if (m_cupsHeader.cupsColorSpace != CUPS_CSPACE_RGBW)
	{
	    rgbRaster = pKRGBRaster;
	}
        if (m_iLogLevel & SAVE_INPUT_RASTERS)
	{
	    char    szFileName[32];
	    sprintf (szFileName, "/tmp/hpcupsc_%d.bmp", iPageNum);
	    if (m_cupsHeader.cupsColorSpace == CUPS_CSPACE_RGBW ||
	        m_cupsHeader.cupsColorSpace == CUPS_CSPACE_RGB)
	    {
	        cfp = fopen (szFileName, "w");
	        chmod (szFileName, S_IRUSR | S_IWUSR | S_IRGRP | S_IROTH);
	    }
	    if (m_cupsHeader.cupsColorSpace == CUPS_CSPACE_RGBW ||
	        m_cupsHeader.cupsColorSpace == CUPS_CSPACE_K)
	    {
	        szFileName[11] = 'k';
	        kfp = fopen (szFileName, "w");
	        chmod (szFileName, S_IRUSR | S_IWUSR | S_IRGRP | S_IROTH);
	    }
	    bitmap.WriteBMPHeader (cfp, m_cupsHeader.cupsWidth, m_cupsHeader.cupsHeight, COLOR_RASTER);
	    bitmap.WriteBMPHeader (kfp, m_cupsHeader.cupsWidth, m_cupsHeader.cupsHeight, BLACK_RASTER);
	}
	m_pSys->SendPreviousPage ();
	for (int y = 0; y < (int) m_cupsHeader.cupsHeight; y++)
	{
	    cupsRasterReadPixels (cups_raster, pKRGBRaster, m_cupsHeader.cupsBytesPerLine);
	    color_raster = rgbRaster;
	    black_raster = kRaster;
	    if (isBlankRaster (pKRGBRaster, (int) m_cupsHeader.cupsBytesPerLine))
	    {
	        color_raster = NULL;
		black_raster = NULL;
	    }
	    doKSeparation (pKRGBRaster, black_raster, color_raster);
	    err = m_pSys->pJob->SendRasters (black_raster, color_raster);
	    if (err != NO_ERROR)
	    {
	        iStatus = 1;
		break;
	    }
	    bitmap.WriteBMPRaster (cfp, color_raster, m_cupsHeader.cupsWidth, COLOR_RASTER);
	    bitmap.WriteBMPRaster (kfp, black_raster, m_cupsHeader.cupsWidth/8, BLACK_RASTER);
	}
	iStatus = (int) m_pSys->pJob->NewPage ();
	if (iStatus != 0)
	{
	    break;
	}
    }
    if (pKRGBRaster)
    {
        delete [] pKRGBRaster;
    }
    if (kRaster && m_cupsHeader.cupsColorSpace != CUPS_CSPACE_K)
    {
        delete [] kRaster;
    }
    if (m_cupsHeader.cupsColorSpace == CUPS_CSPACE_RGBW)
    {
        delete [] rgbRaster;
    }
    if (cfp)
    {
        fclose (cfp);
    }
    if (kfp)
    {
        fclose (kfp);
    }
    return iStatus;
}

void HPCups::doKSeparation (BYTE *pKRGBRaster, BYTE *black_raster, BYTE *color_raster)
{
    
static BYTE pixel_value[8] = {0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01};

    if (black_raster == NULL || m_cupsHeader.cupsColorSpace != CUPS_CSPACE_RGBW)
    {
        return;
    }

    int    k = 0;
    BYTE   *pIn = pKRGBRaster;
    BYTE   kVal = 0;
    BYTE   b;
    BYTE   *rgb   = color_raster;
    BYTE   *black = black_raster;
    memset (black_raster, 0, m_cupsHeader.cupsWidth);

    for (unsigned int i = 0; i < m_cupsHeader.cupsWidth; i++)
    {
	rgb[0] = *pIn++;
	rgb[1] = *pIn++;
	rgb[2] = *pIn++;
	b = *pIn++;

	if (b != 0 && b != 0xFF)
	{
	    rgb[0] -= (255 - b);
	    rgb[1] -= (255 - b);
	    rgb[2] -= (255 - b);
	}
	else
	{
	    kVal |= (b == 0) ? pixel_value[k] : 0;
	}
	rgb += 3;
	if (k == 7)
	{
	    *black++ = kVal;
	    kVal = 0;
	    k = 0;
	}
	else
	{
	    k++;
	}
    }  // end of for loop
    *black = kVal;
}

BOOL HPCups::isBlankRaster (BYTE *pRaster, int iNumBytes)
{
    if (pRaster == NULL)
    {
        return TRUE;
    }
    if (*pRaster == 0xFF &&
        !(memcmp (pRaster + 1, pRaster, iNumBytes - 1)))
    {
        return TRUE;
    }
    return FALSE;
}

void HPCups::printcupsHeader ()
{
    BUG("DEBUG: startPage...\n");
    BUG("DEBUG: MediaClass = \"%s\"\n", m_cupsHeader.MediaClass);
    BUG("DEBUG: MediaColor = \"%s\"\n", m_cupsHeader.MediaColor);
    BUG("DEBUG: MediaType = \"%s\"\n", m_cupsHeader.MediaType);
    BUG("DEBUG: OutputType = \"%s\"\n", m_cupsHeader.OutputType);
    BUG("DEBUG: AdvanceDistance = %d\n", m_cupsHeader.AdvanceDistance);
    BUG("DEBUG: AdvanceMedia = %d\n", m_cupsHeader.AdvanceMedia);
    BUG("DEBUG: Collate = %d\n", m_cupsHeader.Collate);
    BUG("DEBUG: CutMedia = %d\n", m_cupsHeader.CutMedia);
    BUG("DEBUG: Duplex = %d\n", m_cupsHeader.Duplex);
    BUG("DEBUG: HWResolution = [ %d %d ]\n", m_cupsHeader.HWResolution[0], m_cupsHeader.HWResolution[1]);
    BUG("DEBUG: ImagingBoundingBox = [ %d %d %d %d ]\n",
               m_cupsHeader.ImagingBoundingBox[0], m_cupsHeader.ImagingBoundingBox[1],
               m_cupsHeader.ImagingBoundingBox[2], m_cupsHeader.ImagingBoundingBox[3]);
    BUG("DEBUG: InsertSheet = %d\n", m_cupsHeader.InsertSheet);
    BUG("DEBUG: Jog = %d\n", m_cupsHeader.Jog);
    BUG("DEBUG: LeadingEdge = %d\n", m_cupsHeader.LeadingEdge);
    BUG("DEBUG: Margins = [ %d %d ]\n", m_cupsHeader.Margins[0], m_cupsHeader.Margins[1]);
    BUG("DEBUG: ManualFeed = %d\n", m_cupsHeader.ManualFeed);
    BUG("DEBUG: MediaPosition = %d\n", m_cupsHeader.MediaPosition);
    BUG("DEBUG: MediaWeight = %d\n", m_cupsHeader.MediaWeight);
    BUG("DEBUG: MirrorPrint = %d\n", m_cupsHeader.MirrorPrint);
    BUG("DEBUG: NegativePrint = %d\n", m_cupsHeader.NegativePrint);
    BUG("DEBUG: NumCopies = %d\n", m_cupsHeader.NumCopies);
    BUG("DEBUG: Orientation = %d\n", m_cupsHeader.Orientation);
    BUG("DEBUG: OutputFaceUp = %d\n", m_cupsHeader.OutputFaceUp);
    BUG("DEBUG: PageSize = [ %d %d ]\n", m_cupsHeader.PageSize[0], m_cupsHeader.PageSize[1]);
    BUG("DEBUG: Separations = %d\n", m_cupsHeader.Separations);
    BUG("DEBUG: TraySwitch = %d\n", m_cupsHeader.TraySwitch);
    BUG("DEBUG: Tumble = %d\n", m_cupsHeader.Tumble);
    BUG("DEBUG: cupsWidth = %d\n", m_cupsHeader.cupsWidth);
    BUG("DEBUG: cupsHeight = %d\n", m_cupsHeader.cupsHeight);
    BUG("DEBUG: cupsMediaType = %d\n", m_cupsHeader.cupsMediaType);
    BUG("DEBUG: cupsRowCount = %d\n", m_cupsHeader.cupsRowCount);
    BUG("DEBUG: cupsRowStep = %d\n", m_cupsHeader.cupsRowStep);
    BUG("DEBUG: cupsBitsPerColor = %d\n", m_cupsHeader.cupsBitsPerColor);
    BUG("DEBUG: cupsBitsPerPixel = %d\n", m_cupsHeader.cupsBitsPerPixel);
    BUG("DEBUG: cupsBytesPerLine = %d\n", m_cupsHeader.cupsBytesPerLine);
    BUG("DEBUG: cupsColorOrder = %d\n", m_cupsHeader.cupsColorOrder);
    BUG("DEBUG: cupsColorSpace = %d\n", m_cupsHeader.cupsColorSpace);
    BUG("DEBUG: cupsCompression = %d\n", m_cupsHeader.cupsCompression);
    BUG("DEBUG: cupsPageSizeName = %s\n", m_cupsHeader.cupsPageSizeName);
    BUG("DEBUG: cupsInteger0 = %d\n", m_cupsHeader.cupsInteger[0]); // Page Size
    BUG("DEBUG: cupsInteger1 = %d\n", m_cupsHeader.cupsInteger[1]); // Speedmech
    BUG("DEBUG: cupsInteger2 = %d\n", m_cupsHeader.cupsInteger[2]); // Dry time
    BUG("DEBUG: cupsInteger3 = %d\n", m_cupsHeader.cupsInteger[3]); // Filesize
    BUG("DEBUG: cupsInteger4 = %d\n", m_cupsHeader.cupsInteger[4]); // Redeye
    BUG("DEBUG: cupsInteger5 = %d\n", m_cupsHeader.cupsInteger[5]); // Photofix
}

void HPCups::CancelJob ()
{
    BYTE byResetLIDIL[] =  {0x24, 0x00, 0x10, 0x00, 0x06, 0x00, 0x00, 0x00,
                            0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x24};
    PRINTER_TYPE    pt;
    DWORD   size = 4096;
    BYTE    buffer[4098];
    memset (buffer, 0, size);
    pt = m_pSys->pPC->SelectedDevice();
    switch(pt)
    {
	case ePScript:
	    break;
	case eDJ3320:
	case eDJ3600:
	case eDJ4100:
        {
            memcpy (buffer + 4080, byResetLIDIL, 16);
            m_pSys->ToDevice ((const BYTE *) buffer, &size);
	    break;
        }
	case eQuickConnect:
	    break;
        default:
        {
            memcpy (buffer + 4087, "\x1B%-12345X", 9);
            m_pSys->ToDevice ((const BYTE *) buffer, &size);
        }
    }

    m_pSys->OutputPath = -1;    // so no more output is sent to the printer
    if (m_pSys->pJob != NULL)
        delete m_pSys->pJob;
    if (m_pSys->pPC != NULL)
        delete m_pSys->pPC;
    delete m_pSys;
    exit (0);
}

static HPCups    hpCups;
void CancelPrintJob (int sig)
{
    hpCups.CancelJob ();
    exit (0);
}

int main (int argc, char **argv)
{
    int iRet = hpCups.ProcessJob (argc, argv);
    BUG("hpcups: returning status %d from main", iRet);
    return iRet;
}

