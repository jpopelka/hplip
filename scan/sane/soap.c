/************************************************************************************\

  soap.c - HP SANE backend support for soap based multi-function peripherals

  (c) 2006,2008 Copyright Hewlett-Packard Development Company, LP

  Permission is hereby granted, free of charge, to any person obtaining a copy 
  of this software and associated documentation files (the "Software"), to deal 
  in the Software without restriction, including without limitation the rights 
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies 
  of the Software, and to permit persons to whom the Software is furnished to do 
  so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in all
  copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS 
  FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR 
  COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER 
  IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION 
  WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

\************************************************************************************/

#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include <sys/socket.h>
#include <netdb.h>
#include <stdarg.h>
#include <syslog.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <fcntl.h>
#include <math.h>
#include "sane.h"
#include "saneopts.h"
#include "hpmud.h"
#include "hpip.h"
#include "common.h"
#include "soap.h"
#include "http.h"
#include "dime.h"

#define DEBUG_DECLARE_ONLY
#include "sanei_debug.h"

#define SOAP_CONTRAST_MIN -127
#define SOAP_CONTRAST_MAX 127
#define SOAP_CONTRAST_DEFAULT 0

#define MM_PER_INCH     25.4

enum SOAP_OPTION_NUMBER
{ 
   SOAP_OPTION_COUNT = 0,
   SOAP_OPTION_GROUP_SCAN_MODE,
                   SOAP_OPTION_SCAN_MODE,
                   SOAP_OPTION_SCAN_RESOLUTION,
   SOAP_OPTION_GROUP_ADVANCED,
                   SOAP_OPTION_CONTRAST,
                   SOAP_OPTION_COMPRESSION,
                   SOAP_OPTION_JPEG_QUALITY,
   SOAP_OPTION_GROUP_GEOMETRY,
                   SOAP_OPTION_TL_X,
                   SOAP_OPTION_TL_Y,
                   SOAP_OPTION_BR_X,
                   SOAP_OPTION_BR_Y,
   SOAP_OPTION_MAX
};

#define MAX_LIST_SIZE 32
#define MAX_STRING_SIZE 32

enum SCAN_FORMAT
{
   SF_HPRAW = 1,
   SF_JFIF,
   SF_MMR,
   SF_MAX
};

enum DOCUMENT_TYPE 
{
   DT_AUTO = 1,
   DT_MAX,
};

enum COLOR_ENTRY
{
   CE_BLACK_AND_WHITE1 = 1,  /* Windows converts GRAY8 to MONO. Ditto for us. */
   CE_GRAY8, 
   CE_RGB24, 
   CE_RGB48,      /* for test only */
   CE_MAX
};

enum SCANNER_STATE
{
   SS_IDLE = 1, 
   SS_PROCESSING,
   SS_STOPPED,
};

enum SCANNER_STATE_REASON
{
   SSR_ATTENTION_REQUIRED = 1,
   SSR_CALIBRATING,
   SSR_COVER_OPEN,
   SSR_INPUT_TRAY_EMPTY,
   SSR_INTERNAL_STORAGE_FULL,
   SSR_LAMP_ERROR,
   SSR_LAMP_WARMING,
   SSR_MEDIA_JAM,
   SSR_BUSY,
   SSR_NONE,
};

struct media_size
{
   int width;         /* in 1/1000 of an inch */
   int height;        /* in 1/1000 of an inch */
};

struct device_settings
{
   enum SCAN_FORMAT formats[SF_MAX];
   int jpeg_quality_factor_supported;      /* 0=false, 1=true */
   enum DOCUMENT_TYPE docs[DT_MAX];
   int document_size_auto_detect_supported;  /* 0=false, 1=true */
   int feeder_capacity;  
   int rotation;                      /* needed adf front side image rotation */
   int duplex_rotation;               /* needed adf back side image rotation */
};

struct device_platen
{
   enum COLOR_ENTRY color[CE_MAX];
   struct media_size minimum_size;
   struct media_size maximum_size;
   struct media_size optical_resolution;
   int flatbed_supported;   /* 0=false, 1=true */        
};

struct device_adf
{
   int supported;   /* 0=false, 1=true */
   int duplex_supported;  /* 0=false, 1=true */
   struct media_size minimum_size;
   struct media_size maximum_size;
   struct media_size optical_resolution;
};

struct scanner_configuration
{
   struct device_settings settings;
   struct device_platen platen;
   struct device_adf adf;
};

struct scanner_status
{
   char *current_time;
   enum SCANNER_STATE state;
   enum SCANNER_STATE_REASON reason;
   int paper_in_adf;   /* 0=false, 1=true */
   int scan_to_available;  /* 0=false, 1=true */
};

struct wscn_scan_elements
{
   struct scanner_configuration config;
   struct scanner_status status;
   char model_number[32];
};

struct wscn_create_scan_job_response
{
   int jobid;
   int pixels_per_line;
   int lines;            /* number of lines */
   int bytes_per_line;   /* zero if jpeg */
   enum SCAN_FORMAT format;
   int jpeg_quality_factor;
   int images_to_transfer;     /* number of images to scan */
   enum DOCUMENT_TYPE doc;
   struct media_size input_size;
   int scan_region_xoffset;
   int scan_region_yoffset;
   int scan_region_width;
   int scan_region_height;
   enum COLOR_ENTRY color;
   struct media_size resolution;
};

struct soap_session
{
   char *tag;  /* handle identifier */
   HPMUD_DEVICE dd;  /* hpiod device descriptor */
   HPMUD_CHANNEL cd;  /* hpiod soap channel descriptor */
   char uri[HPMUD_LINE_SIZE];
   char model[HPMUD_LINE_SIZE];
   int scantype;

   IP_IMAGE_TRAITS imageTraits;   /* specified by image header */      
   struct wscn_scan_elements elements;       /* scanner elements (valid after sane_open and sane_start) */
   char scan_id[HPMUD_LINE_SIZE];    /* unique scan job identifier */

   SANE_Option_Descriptor option[SOAP_OPTION_MAX];

   SANE_String_Const scanModeList[CE_MAX];
   enum COLOR_ENTRY scanModeMap[CE_MAX];
   enum COLOR_ENTRY currentScanMode;

   SANE_Int resolutionList[MAX_LIST_SIZE];
   SANE_Int currentResolution;

   SANE_Range contrastRange;
   SANE_Int currentContrast;

   SANE_String_Const compressionList[SF_MAX];
   enum SCAN_FORMAT compressionMap[SF_MAX];
   enum SCAN_FORMAT currentCompression; 

   SANE_Range jpegQualityRange;
   SANE_Int currentJpegQuality;

   SANE_Range tlxRange, tlyRange, brxRange, bryRange;
   SANE_Fixed currentTlx, currentTly, currentBrx, currentBry;
   SANE_Fixed effectiveTlx, effectiveTly, effectiveBrx, effectiveBry;
   SANE_Fixed minWidth, minHeight;

   HTTP_HANDLE http_handle;
   DIME_HANDLE dime_handle;
   IP_HANDLE ipHandle;

   int index;                    /* dime buffer index */
   int cnt;                      /* dime buffer count */
   unsigned char buf[16384];    /* dime buffer */
};

/* Following elements must match their associated enum table. */
static const char *sf_element[SF_MAX] = { "", "scanDIB", "scanJFIF", "scanMMRf" };  /* SCAN_FORMAT */
static const char *sf_compression[SF_MAX] = { "", "scanNoCompression", "scanJPEG", "scanMMR" };  /* SCAN_FORMAT (compression) */
static const char *ce_element[CE_MAX] = { "", "scanBlackandWhite1", "scanGrayScale8", "scanRGB24", "scanRGB48" };   /* COLOR_ENTRY */

static struct soap_session *session = NULL;   /* assume one sane_open per process */

#define POST_HEADER "POST / HTTP/1.1\r\nHost: http:0\r\nUser-Agent: gSOAP/2.7\r\nContent-Type: \
application/soap+xml; charset=utf-8\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n"

#define GET_SCANNER_ELEMENTS "19E\r\n<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<SOAP-ENV:Envelope \
xmlns:SOAP-ENV=\"http://www.w3.org/2003/05/soap-envelope\" xmlns:SOAP-ENC=\"http://www.w3.org/2003/05/soap-encoding\" \
xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\" \
xmlns:wscn=\"http://tempuri.org/wscn.xsd\"><SOAP-ENV:Body><wscn:GetScannerElements></wscn:GetScannerElements></SOAP-ENV:Body></SOAP-ENV:Envelope>\r\n0\r\n\r\n"

#define CREATE_SCAN_JOB_REQUEST "<?xml version=\"1.0\" encoding=\"UTF-8\"?><SOAP-ENV:Envelope \
xmlns:SOAP-ENV=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:SOAP-ENC=\"http://schemas.xmlsoap.org/soap/encoding/\" \
xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\" \
xmlns:wscn=\"http://tempuri.org/wscn.xsd\"><SOAP-ENV:Body><wscn:InitiateScanRequest><ScanTicket><JobDescription>\
<JobName>%s</JobName><JobOriginatingUsername>Eric Cartman</JobOriginatingUsername></JobDescription>\
<DocumentParameters><Format>%s</Format><InputSource>scanPlaten</InputSource><ContentType>scanAuto</ContentType>\
<DocumentCompression><CompressionType>%s</CompressionType><JPEGQualityFactor>%d</JPEGQualityFactor></DocumentCompression>\
<Contrast>%d</Contrast><ScanRegion><ScanRegionXOffset>%d</ScanRegionXOffset><ScanRegionYOffset>%d</ScanRegionYOffset>\
<ScanRegionWidth>%d</ScanRegionWidth><ScanRegionHeight>%d</ScanRegionHeight></ScanRegion>\
<ColorProcessing>%s</ColorProcessing><Resolution><ResolutionWidth>%d</ResolutionWidth>\
<ResolutionHeight>%d</ResolutionHeight></Resolution><PadImage>true</PadImage><GammaCorrection>2.2</GammaCorrection>\
</DocumentParameters></ScanTicket><DestinationID>PC</DestinationID><ScanIdentifier>linux-rocks</ScanIdentifier>\
</wscn:InitiateScanRequest></SOAP-ENV:Body></SOAP-ENV:Envelope>"

#define CANCEL_JOB_REQUEST "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<SOAP-ENV:Envelope xmlns:SOAP-ENV=\"http://www.w3.org/2003/05/soap-envelope\" \
xmlns:SOAP-ENC=\"http://www.w3.org/2003/05/soap-encoding\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" \
xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\" xmlns:wscn=\"http://tempuri.org/wscn.xsd\"><SOAP-ENV:Body><wscn:CancelJob>\
<ScanIdentifier>%s</ScanIdentifier>\
</wscn:CancelJob></SOAP-ENV:Body></SOAP-ENV:Envelope>"

#define ZERO_FOOTER "\r\n0\r\n\r\n"

int __attribute__ ((visibility ("hidden"))) get_array_size(const char *tag)
{
   char *p, *tail;

   if ((p = strstr(tag, "arraySize=\"")))
      return strtol(p+11, &tail, 10);
   else
      return 0;
}

/* Get xml element from the buffer. The returned element is zero terminated. */
int __attribute__ ((visibility ("hidden"))) get_element(const char *buf, int buf_size, char *element, int element_size, char **tail)
{
   int i, j;

   element[0]=0;

   for (i=0, j=0; buf[i] != '<' && j < (element_size-1) && i < buf_size; i++)
      element[j++] = buf[i];

   element[j]=0;   /* zero terminate */

   if (tail != NULL)
      *tail = (char *)buf + i;   /* tail points to next tag */

   return j;  /* length does not include zero termination */
}

/* Get next xml tag from the buffer. The returned xml tag is zero terminated. */
int __attribute__ ((visibility ("hidden"))) get_tag(const char *buf, int buf_size, char *tag, int tag_size, char **tail)
{
   int i=0, j=0, dd=0, lf=0;

   tag[0]=0;

   while (1)
   {
      for (; buf[i] != '<' && i < buf_size; i++);  /* eat up space before '<' */

      if (buf[i] != '<')
         break;

      if (i < (buf_size-4) && (strncmp(&buf[i], "<!--", 4) == 0))
      {
         for (; buf[i] != '>' && i < buf_size; i++);  /* eat comment line */
         i++;
         continue;
      }
   
      i++; /* eat '<' */

      for (j=0; buf[i] != '>' && j < (tag_size-1) && i < buf_size; i++)
      {
         if (buf[i] == '\r')
         {
            tag[j++] = '\n';   /* convert CR to LF */
            lf=1;            /* set remove back-to-back LF flag */
         }
         else if (buf[i] == '\n')
         {
            if (!lf)
               tag[j++] = buf[i]; 
         }
         else if (buf[i] == ' ')
         {
            if (!dd)
            {
               tag[j++] = buf[i];
               dd=1;             /* set remove back-to-back space flag */
            }
         }
         else
         {
            tag[j++] = buf[i];
            dd=0;
            lf=0;
         }
      }
      break;
   }
 
   if (i < buf_size)
      i++;     /* eat '>' */

   tag[j]=0;  /* zero terminate */

   if (tail != NULL)
      *tail = (char *)buf + i;   /* tail points to next tag */

   return j;   /* length does no include zero termination */
}

static int parse_scan_elements(const char *payload, int size, struct wscn_scan_elements *elements)
{
   char tag[512];
   char value[128];
   int i, n;
   char *tail=(char *)payload;

   memset(elements, 0, sizeof(struct wscn_scan_elements));

   while (1)
   {
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      
      if (!tag[0])
         break;     /* done */

      if (strncmp(tag, "FormatSupported", 15) == 0)     /* note arrays must use strncmp */
      {
         n = get_array_size(tag);
         for (i=0; i<n; i++)
         {
            get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail); /* <item> */
            get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
            get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail); /* </item> */
            if (strcmp(value, sf_element[SF_JFIF]) == 0)
               elements->config.settings.formats[SF_JFIF] = SF_JFIF;
            else if (strcmp(value, sf_element[SF_HPRAW]) == 0)
               elements->config.settings.formats[SF_HPRAW] = SF_HPRAW;
            else if (strcmp(value, sf_element[SF_MMR]) == 0)
               elements->config.settings.formats[SF_MMR] = 0;        /* not used */
            else
               BUG("unknowned element=%s\n", value);
            DBG6("FormatSupported:%s\n", value);
         }
      }
      else if (strcmp(tag, "JPEGQualityFactorSupported") == 0)
      {
         get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
         if (strcmp(value, "true") == 0)
            elements->config.settings.jpeg_quality_factor_supported = 1;
         DBG6("QualityFactorSupported:%s\n", value);
      }
      else if (strncmp(tag, "ColorSupported", 14) == 0)
      {
         n = get_array_size(tag);
         for (i=0; i<n; i++)
         {
            get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail); /* <item> */
            get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
            get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail); /* </item> */
            if (strcmp(value, ce_element[CE_BLACK_AND_WHITE1]) == 0)
               elements->config.platen.color[CE_BLACK_AND_WHITE1] = CE_BLACK_AND_WHITE1;
            else if (strcmp(value, ce_element[CE_GRAY8]) == 0)
               elements->config.platen.color[CE_GRAY8] = CE_GRAY8;
            else if (strcmp(value, ce_element[CE_RGB24]) == 0)
               elements->config.platen.color[CE_RGB24] = CE_RGB24;
            else if (strcmp(value, ce_element[CE_RGB48]) == 0)
               elements->config.platen.color[CE_RGB48] = 0;  /* for test only */
            else
               BUG("unknowned element=%s\n", value);
            DBG6("ColorSupported:%s\n", value);
         }
      }
      else if (strcmp(tag, "PlatenMinimumSize") == 0)
      {
         for (i=0; i<2; i++)
         {
            get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);   /* <xxx> */
            if (strcmp(tag, "DimensionsWidth") == 0)
            {
               get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
               elements->config.platen.minimum_size.width = strtol(value, NULL, 10);
            }
            else
            {
               get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
               elements->config.platen.minimum_size.height = strtol(value, NULL, 10);
            }
            DBG6("PlatenMinimumSize:%s:%s\n", tag, value);
            get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);   /* </xxx> */
         }
      }
      else if (strcmp(tag, "PlatenMaximumSize") == 0)
      {
         for (i=0; i<2; i++)
         {
            get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);   /* <xxx> */
            if (strcmp(tag, "DimensionsWidth") == 0)
            {
               get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
               elements->config.platen.maximum_size.width = strtol(value, NULL, 10);
            }
            else
            {
               get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
               elements->config.platen.maximum_size.height = strtol(value, NULL, 10);
            }
            DBG6("PlatenMaximumSize:%s:%s\n", tag, value);
            get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);   /* </xxx> */
         }
      }
      else if (strcmp(tag, "PlatenOpticalResolution") == 0)
      {
         for (i=0; i<2; i++)
         {
            get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);   /* <xxx> */
            if (strcmp(tag, "ResolutionWidth") == 0)
            {
               get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
               elements->config.platen.optical_resolution.width = strtol(value, NULL, 10);
            }
            else
            {
               get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
               elements->config.platen.optical_resolution.height = strtol(value, NULL, 10);
            }
            DBG6("PlatenOpticalResolution:%s:%s\n", tag, value);
            get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);   /* </xxx> */
         }
      }
      else if (strcmp(tag, "ScannerState") == 0)
      {
         get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
         if (strcmp(value, "scanIdle") == 0)
            elements->status.state = SS_IDLE;
         else if (strcmp(value, "scanProcessing") == 0)
            elements->status.state = SS_PROCESSING;
         else if (strcmp(value, "scanStopped") == 0)
            elements->status.state = SS_STOPPED;
         else
            BUG("unknowned element=%s\n", value);
         DBG6("ScannerState:%s\n", value);
      }
   }  /* end while (1) */

   return 0;
}

static int read_http_payload(struct soap_session *ps, char *payload, int max_size, int sec_timeout, int *bytes_read)
{
   int stat=1, total=0, len;
   int tmo=sec_timeout;
   enum HTTP_RESULT ret;

   *bytes_read = 0;

   if (http_read_header(ps->http_handle, payload, max_size, tmo, &len) != HTTP_R_OK)
      goto bugout; 

   while (total < max_size)
   {
      ret = http_read_payload(ps->http_handle, payload+total, max_size-total, tmo, &len);
      if (!(ret == HTTP_R_OK || ret == HTTP_R_EOF))
         goto bugout;
      total+=len;
      tmo=1;
      if (ret == HTTP_R_EOF)
         break;    /* done */
   }
   *bytes_read = total;
   stat=0;

bugout:
   return stat;
}

static int get_scanner_elements(struct soap_session *ps, struct wscn_scan_elements *elements)
{
   int bytes_read;
   int stat=1, tmo=EXCEPTION_TIMEOUT;
   char buf[4096];

   if (http_open(ps->dd, HPMUD_S_SOAP_SCAN, &ps->http_handle) != HTTP_R_OK)
   {
      BUG("unable to open http connection %s\n", session->uri);
      goto bugout;
   }

   /* Write the http post header. Note do not send null termination byte. */
   if (http_write(ps->http_handle, POST_HEADER, sizeof(POST_HEADER)-1, tmo) != HTTP_R_OK)
   {
      BUG("unable to get_scanner_elements %s\n", ps->uri);
      goto bugout;
   }

   /* Write the xml payload. */
   if (http_write(ps->http_handle, GET_SCANNER_ELEMENTS, sizeof(GET_SCANNER_ELEMENTS)-1, tmo) != HTTP_R_OK)
   {
      BUG("unable to get_scanner_elements %s\n", ps->uri);
      goto bugout;
   }

   /* Read http response. */
   if (read_http_payload(ps, buf, sizeof(buf), tmo, &bytes_read))
      goto bugout;

   parse_scan_elements(buf, bytes_read, elements);

   stat=0;

bugout:
   if (ps->http_handle)
   {
      http_close(ps->http_handle);
      ps->http_handle = 0;
   }
   return stat;   
};

static int cancel_job(struct soap_session *ps)
{
   int bytes_read, len, footer_len;
   int stat=1, tmo=EXCEPTION_TIMEOUT;
   char buf[2048];
   char footer[32];

   if (ps->scan_id[0] == 0)
      goto bugout;

   if (http_open(ps->dd, HPMUD_S_SOAP_SCAN, &ps->http_handle) != HTTP_R_OK)
   {
      BUG("unable to open http connection %s\n", session->uri);
      goto bugout;
   }

   /* Write the http post header. Note do not send null termination byte. */
   if (http_write(ps->http_handle, POST_HEADER, sizeof(POST_HEADER)-1, tmo) != HTTP_R_OK)
   {
      BUG("unable to cancel_job %s\n", ps->uri);
      goto bugout;
   }

   len = snprintf(buf, sizeof(buf), CANCEL_JOB_REQUEST, ps->scan_id);
   ps->scan_id[0] = 0;

   /* Write footer for xml payload. */
   footer_len = snprintf(footer, sizeof(footer), "%x\r\n", len);
   if (http_write(ps->http_handle, footer, footer_len, 1) != HTTP_R_OK)
   {
      BUG("unable to cancel_job %s\n", ps->uri);
      goto bugout;
   }

   /* Write the xml payload. */
   if (http_write(ps->http_handle, buf, len, 1) != HTTP_R_OK)
   {
      BUG("unable to cancel_scan %s\n", ps->uri);
      goto bugout;
   }

   /* Write zero footer. */
   if (http_write(ps->http_handle, ZERO_FOOTER, sizeof(ZERO_FOOTER)-1, 1) != HTTP_R_OK)
   {
      BUG("unable to cancel_scan %s\n", ps->uri);
      goto bugout;
   }

   /* Read response. */
   if (read_http_payload(ps, buf, sizeof(buf), tmo, &bytes_read))
      goto bugout;

   stat=0;

bugout:
   if (ps->http_handle)
   {
      http_close(ps->http_handle);
      ps->http_handle = 0;
   }
   return stat;   
};

/* Set scan parameters. If scan has started, use actual known parameters otherwise estimate. */  
static int scan_parameters(struct soap_session *ps, SANE_Parameters *pp, int scan_started)
{
   double unalignedPixel;
   int milliInchWidth = (int)(SANE_UNFIX(ps->effectiveBrx - ps->effectiveTlx)/MM_PER_INCH*1000.0);
   int milliInchHeight = (int)(SANE_UNFIX(ps->effectiveBry - ps->effectiveTly)/MM_PER_INCH*1000.0);

   pp->last_frame = SANE_TRUE;

   /*
    * Set scan parameters based on best guess. Since there is no header for raw data to determine exact pixels_per_row
    * and number_of_rows, we must match firmware calculations. Even though this is lossy, convert from mm to milli-inch then
    * calculate scan parameters.
    */
   //   pp->lines = (int)(SANE_UNFIX(ps->effectiveBry - ps->effectiveTly)/MM_PER_INCH*ps->currentResolution);
   pp->lines = floor(milliInchHeight/1000.0*ps->currentResolution);
   //   pp->pixels_per_line = floor(SANE_UNFIX(ps->effectiveBrx - ps->effectiveTlx)/MM_PER_INCH*ps->currentResolution);
   pp->pixels_per_line = floor(milliInchWidth/1000.0*ps->currentResolution);

   switch(ps->currentScanMode)
   {
      case CE_BLACK_AND_WHITE1:
         pp->format = SANE_FRAME_GRAY;     /* lineart */
         pp->depth = 1;
         unalignedPixel = milliInchWidth/1000.0*ps->currentResolution;
         pp->pixels_per_line = floor(unalignedPixel - fmod(unalignedPixel, 8));   /* byte align 1-bit pixels */
         pp->bytes_per_line = BYTES_PER_LINE(pp->pixels_per_line, pp->depth * 1);   /* best guess */
         if (scan_started)
         {  /* Use known scan parameters. Use IP for jpeg and hpraw because GRAY8 is converted to MONO. */
            pp->lines = ps->imageTraits.lNumRows;
            pp->pixels_per_line = ps->imageTraits.iPixelsPerRow;
            pp->bytes_per_line = BYTES_PER_LINE(pp->pixels_per_line, pp->depth * 1);
         }
         break;
      case CE_GRAY8:
         pp->format = SANE_FRAME_GRAY;     /* grayscale */
         pp->depth = 8;
         pp->bytes_per_line = BYTES_PER_LINE(pp->pixels_per_line, pp->depth * 1);
         if (scan_started)
         {  /* Use known scan parameters. */
            pp->lines = ps->imageTraits.lNumRows;
            pp->pixels_per_line = ps->imageTraits.iPixelsPerRow;
            pp->bytes_per_line = BYTES_PER_LINE(pp->pixels_per_line, pp->depth * 1);
         }
         break;
      case CE_RGB24:
      default:
         pp->format = SANE_FRAME_RGB;      /* color */
         pp->depth = 8;
         pp->bytes_per_line = BYTES_PER_LINE(pp->pixels_per_line, pp->depth * 3);
         if (scan_started)
         {  /* Use known scan parameters. */
            pp->lines = ps->imageTraits.lNumRows;
            pp->pixels_per_line = ps->imageTraits.iPixelsPerRow;
            pp->bytes_per_line = BYTES_PER_LINE(pp->pixels_per_line, pp->depth * 3);
         }
         break;
   }
   return 0;
}

/* Get raw data (ie: uncompressed data) from image processor. */
static int get_ip_data(struct soap_session *ps, SANE_Byte *data, SANE_Int maxLength, SANE_Int *length)
{
   int ip_ret=IP_INPUT_ERROR, len;
   unsigned int outputAvail=maxLength, outputUsed=0, outputThisPos;
   unsigned char *input, *output = data;
   unsigned int inputAvail, inputUsed=0, inputNextPos;
   enum DIME_RESULT ret;

   if (!ps->ipHandle)
   {
      BUG("invalid ipconvert state\n");
      goto bugout;
   }      

   /* See if we need more scan data. */
   if (ps->cnt==0)
   {
      /* Get some data. */
      ret = dime_read(ps->dime_handle, ps->buf, sizeof(ps->buf), EXCEPTION_TIMEOUT, &len);
      if (!(ret == DIME_R_OK || ret == DIME_R_EOF))
      {
         BUG("unable to read scan data ret=%d\n", ret);
         goto bugout;
      }   
      ps->cnt += len;
   }
   else
   {
      ret = HTTP_R_OK;  /* use left over data first */ 
   }
     
   if (ret == HTTP_R_EOF)
   {
      input = NULL;   /* no more scan data, flush ipconvert pipeline */
      inputAvail = 0;
   }
   else
   {
      input = &ps->buf[ps->index];
      inputAvail = ps->cnt;
   }

   /* Transform input data to output. Note, output buffer may consume more bytes than input buffer (ie: jpeg to raster). */
   ip_ret = ipConvert(ps->ipHandle, inputAvail, input, &inputUsed, &inputNextPos, outputAvail, output, &outputUsed, &outputThisPos);

   DBG6("cnt=%d index=%d input=%p inputAvail=%d inputUsed=%d inputNextPos=%d output=%p outputAvail=%d outputThisPos=%d\n", ps->cnt, ps->index, input, 
         inputAvail, inputUsed, inputNextPos, output, outputAvail, outputThisPos);

   if (input != NULL)
   {
      if (inputAvail == inputUsed)
      {
         ps->index = ps->cnt = 0;   /* reset buffer */
      }
      else
      {
         ps->cnt -= inputUsed;    /* save left over buffer for next soap_read */
         ps->index += inputUsed;
      }
   }

   if (data)
      *length = outputUsed;

   /* For sane do not send output data simultaneously with IP_DONE. */
   if (ip_ret & IP_DONE && outputUsed)
      ip_ret &= ~IP_DONE;                               

bugout:
   return ip_ret;
}

static int set_scan_mode_side_effects(struct soap_session *ps, enum COLOR_ENTRY scanMode)
{
   int j=0;

   memset(ps->compressionList, 0, sizeof(ps->compressionList));
   memset(ps->compressionMap, 0, sizeof(ps->compressionMap));

   switch (scanMode)
   {
      case CE_BLACK_AND_WHITE1:         /* same as GRAY8 */
      case CE_GRAY8:
      case CE_RGB24:
      default:
         ps->compressionList[j] = STR_COMPRESSION_NONE; 
         ps->compressionMap[j++] = SF_HPRAW;
         ps->compressionList[j] = STR_COMPRESSION_JPEG; 
         ps->compressionMap[j++] = SF_JFIF;
         ps->currentCompression = SF_JFIF;
         ps->option[SOAP_OPTION_JPEG_QUALITY].cap |= SANE_CAP_SOFT_SELECT;   /* enable jpeg quality */        
         break;
   }

   return 0;
}

static struct soap_session *create_session()
{
   struct soap_session *ps;

   if ((ps = malloc(sizeof(struct soap_session))) == NULL)
   {
      BUG("malloc failed: %m\n");
      return NULL;
   }
   memset(ps, 0, sizeof(struct soap_session));
   ps->tag = "SOAP";
   ps->dd = -1;
   ps->cd = -1;

   return ps;
}

static int init_options(struct soap_session *ps)
{
   ps->option[SOAP_OPTION_COUNT].name = "option-cnt";
   ps->option[SOAP_OPTION_COUNT].title = SANE_TITLE_NUM_OPTIONS;
   ps->option[SOAP_OPTION_COUNT].desc = SANE_DESC_NUM_OPTIONS;
   ps->option[SOAP_OPTION_COUNT].type = SANE_TYPE_INT;
   ps->option[SOAP_OPTION_COUNT].unit = SANE_UNIT_NONE;
   ps->option[SOAP_OPTION_COUNT].size = sizeof(SANE_Int);
   ps->option[SOAP_OPTION_COUNT].cap = SANE_CAP_SOFT_DETECT;
   ps->option[SOAP_OPTION_COUNT].constraint_type = SANE_CONSTRAINT_NONE;

   ps->option[SOAP_OPTION_GROUP_SCAN_MODE].name = "mode-group";
   ps->option[SOAP_OPTION_GROUP_SCAN_MODE].title = SANE_TITLE_SCAN_MODE;
   ps->option[SOAP_OPTION_GROUP_SCAN_MODE].type = SANE_TYPE_GROUP;

   ps->option[SOAP_OPTION_SCAN_MODE].name = SANE_NAME_SCAN_MODE;
   ps->option[SOAP_OPTION_SCAN_MODE].title = SANE_TITLE_SCAN_MODE;
   ps->option[SOAP_OPTION_SCAN_MODE].desc = SANE_DESC_SCAN_MODE;
   ps->option[SOAP_OPTION_SCAN_MODE].type = SANE_TYPE_STRING;
   ps->option[SOAP_OPTION_SCAN_MODE].unit = SANE_UNIT_NONE;
   ps->option[SOAP_OPTION_SCAN_MODE].size = MAX_STRING_SIZE;
   ps->option[SOAP_OPTION_SCAN_MODE].cap = SANE_CAP_SOFT_SELECT | SANE_CAP_SOFT_DETECT;
   ps->option[SOAP_OPTION_SCAN_MODE].constraint_type = SANE_CONSTRAINT_STRING_LIST;
   ps->option[SOAP_OPTION_SCAN_MODE].constraint.string_list = ps->scanModeList;

   ps->option[SOAP_OPTION_SCAN_RESOLUTION].name = SANE_NAME_SCAN_RESOLUTION;
   ps->option[SOAP_OPTION_SCAN_RESOLUTION].title = SANE_TITLE_SCAN_RESOLUTION;
   ps->option[SOAP_OPTION_SCAN_RESOLUTION].desc = SANE_DESC_SCAN_RESOLUTION;
   ps->option[SOAP_OPTION_SCAN_RESOLUTION].type = SANE_TYPE_INT;
   ps->option[SOAP_OPTION_SCAN_RESOLUTION].unit = SANE_UNIT_DPI;
   ps->option[SOAP_OPTION_SCAN_RESOLUTION].size = sizeof(SANE_Int);
   ps->option[SOAP_OPTION_SCAN_RESOLUTION].cap = SANE_CAP_SOFT_SELECT | SANE_CAP_SOFT_DETECT;
   ps->option[SOAP_OPTION_SCAN_RESOLUTION].constraint_type = SANE_CONSTRAINT_WORD_LIST;
   ps->option[SOAP_OPTION_SCAN_RESOLUTION].constraint.word_list = ps->resolutionList;

   ps->option[SOAP_OPTION_GROUP_ADVANCED].name = "advanced-group";
   ps->option[SOAP_OPTION_GROUP_ADVANCED].title = STR_TITLE_ADVANCED;
   ps->option[SOAP_OPTION_GROUP_ADVANCED].type = SANE_TYPE_GROUP;
   ps->option[SOAP_OPTION_GROUP_ADVANCED].cap = SANE_CAP_ADVANCED;

   ps->option[SOAP_OPTION_CONTRAST].name = SANE_NAME_CONTRAST;
   ps->option[SOAP_OPTION_CONTRAST].title = SANE_TITLE_CONTRAST;
   ps->option[SOAP_OPTION_CONTRAST].desc = SANE_DESC_CONTRAST;
   ps->option[SOAP_OPTION_CONTRAST].type = SANE_TYPE_INT;
   ps->option[SOAP_OPTION_CONTRAST].unit = SANE_UNIT_NONE;
   ps->option[SOAP_OPTION_CONTRAST].size = sizeof(SANE_Int);
   ps->option[SOAP_OPTION_CONTRAST].cap = SANE_CAP_SOFT_SELECT | SANE_CAP_SOFT_DETECT | SANE_CAP_ADVANCED;
   ps->option[SOAP_OPTION_CONTRAST].constraint_type = SANE_CONSTRAINT_RANGE;
   ps->option[SOAP_OPTION_CONTRAST].constraint.range = &ps->contrastRange;
   ps->contrastRange.min = SOAP_CONTRAST_MIN;
   ps->contrastRange.max = SOAP_CONTRAST_MAX;
   ps->contrastRange.quant = 0;

   ps->option[SOAP_OPTION_COMPRESSION].name = STR_NAME_COMPRESSION;
   ps->option[SOAP_OPTION_COMPRESSION].title = STR_TITLE_COMPRESSION;
   ps->option[SOAP_OPTION_COMPRESSION].desc = STR_DESC_COMPRESSION;
   ps->option[SOAP_OPTION_COMPRESSION].type = SANE_TYPE_STRING;
   ps->option[SOAP_OPTION_COMPRESSION].unit = SANE_UNIT_NONE;
   ps->option[SOAP_OPTION_COMPRESSION].size = MAX_STRING_SIZE;
   ps->option[SOAP_OPTION_COMPRESSION].cap = SANE_CAP_SOFT_SELECT | SANE_CAP_SOFT_DETECT | SANE_CAP_ADVANCED;
   ps->option[SOAP_OPTION_COMPRESSION].constraint_type = SANE_CONSTRAINT_STRING_LIST;
   ps->option[SOAP_OPTION_COMPRESSION].constraint.string_list = ps->compressionList;

   ps->option[SOAP_OPTION_JPEG_QUALITY].name = STR_NAME_JPEG_QUALITY;
   ps->option[SOAP_OPTION_JPEG_QUALITY].title = STR_TITLE_JPEG_QUALITY;
   ps->option[SOAP_OPTION_JPEG_QUALITY].desc = STR_DESC_JPEG_QUALITY;
   ps->option[SOAP_OPTION_JPEG_QUALITY].type = SANE_TYPE_INT;
   ps->option[SOAP_OPTION_JPEG_QUALITY].unit = SANE_UNIT_NONE;
   ps->option[SOAP_OPTION_JPEG_QUALITY].size = sizeof(SANE_Int);
   ps->option[SOAP_OPTION_JPEG_QUALITY].cap = SANE_CAP_SOFT_SELECT | SANE_CAP_SOFT_DETECT | SANE_CAP_ADVANCED;
   ps->option[SOAP_OPTION_JPEG_QUALITY].constraint_type = SANE_CONSTRAINT_RANGE;
   ps->option[SOAP_OPTION_JPEG_QUALITY].constraint.range = &ps->jpegQualityRange;
   ps->jpegQualityRange.min = MIN_JPEG_COMPRESSION_FACTOR;
   ps->jpegQualityRange.max = MAX_JPEG_COMPRESSION_FACTOR;
   ps->jpegQualityRange.quant = 0;

   ps->option[SOAP_OPTION_GROUP_GEOMETRY].name = "geometry-group";
   ps->option[SOAP_OPTION_GROUP_GEOMETRY].title = STR_TITLE_GEOMETRY;
   ps->option[SOAP_OPTION_GROUP_GEOMETRY].type = SANE_TYPE_GROUP;
   ps->option[SOAP_OPTION_GROUP_GEOMETRY].cap = SANE_CAP_ADVANCED;

   ps->option[SOAP_OPTION_TL_X].name = SANE_NAME_SCAN_TL_X;
   ps->option[SOAP_OPTION_TL_X].title = SANE_TITLE_SCAN_TL_X;
   ps->option[SOAP_OPTION_TL_X].desc = SANE_DESC_SCAN_TL_X;
   ps->option[SOAP_OPTION_TL_X].type = SANE_TYPE_FIXED;
   ps->option[SOAP_OPTION_TL_X].unit = SANE_UNIT_MM;
   ps->option[SOAP_OPTION_TL_X].size = sizeof(SANE_Int);
   ps->option[SOAP_OPTION_TL_X].cap = SANE_CAP_SOFT_SELECT | SANE_CAP_SOFT_DETECT;
   ps->option[SOAP_OPTION_TL_X].constraint_type = SANE_CONSTRAINT_RANGE;
   ps->option[SOAP_OPTION_TL_X].constraint.range = &ps->tlxRange;
   ps->tlxRange.min = 0;
   ps->tlxRange.quant = 0;

   ps->option[SOAP_OPTION_TL_Y].name = SANE_NAME_SCAN_TL_Y;
   ps->option[SOAP_OPTION_TL_Y].title = SANE_TITLE_SCAN_TL_Y;
   ps->option[SOAP_OPTION_TL_Y].desc = SANE_DESC_SCAN_TL_Y;
   ps->option[SOAP_OPTION_TL_Y].type = SANE_TYPE_FIXED;
   ps->option[SOAP_OPTION_TL_Y].unit = SANE_UNIT_MM;
   ps->option[SOAP_OPTION_TL_Y].size = sizeof(SANE_Int);
   ps->option[SOAP_OPTION_TL_Y].cap = SANE_CAP_SOFT_SELECT | SANE_CAP_SOFT_DETECT;
   ps->option[SOAP_OPTION_TL_Y].constraint_type = SANE_CONSTRAINT_RANGE;
   ps->option[SOAP_OPTION_TL_Y].constraint.range = &ps->tlyRange;
   ps->tlyRange.min = 0;
   ps->tlyRange.quant = 0;

   ps->option[SOAP_OPTION_BR_X].name = SANE_NAME_SCAN_BR_X;
   ps->option[SOAP_OPTION_BR_X].title = SANE_TITLE_SCAN_BR_X;
   ps->option[SOAP_OPTION_BR_X].desc = SANE_DESC_SCAN_BR_X;
   ps->option[SOAP_OPTION_BR_X].type = SANE_TYPE_FIXED;
   ps->option[SOAP_OPTION_BR_X].unit = SANE_UNIT_MM;
   ps->option[SOAP_OPTION_BR_X].size = sizeof(SANE_Int);
   ps->option[SOAP_OPTION_BR_X].cap = SANE_CAP_SOFT_SELECT | SANE_CAP_SOFT_DETECT;
   ps->option[SOAP_OPTION_BR_X].constraint_type = SANE_CONSTRAINT_RANGE;
   ps->option[SOAP_OPTION_BR_X].constraint.range = &ps->brxRange;
   ps->brxRange.min = 0;
   ps->brxRange.quant = 0;

   ps->option[SOAP_OPTION_BR_Y].name = SANE_NAME_SCAN_BR_Y;
   ps->option[SOAP_OPTION_BR_Y].title = SANE_TITLE_SCAN_BR_Y;
   ps->option[SOAP_OPTION_BR_Y].desc = SANE_DESC_SCAN_BR_Y;
   ps->option[SOAP_OPTION_BR_Y].type = SANE_TYPE_FIXED;
   ps->option[SOAP_OPTION_BR_Y].unit = SANE_UNIT_MM;
   ps->option[SOAP_OPTION_BR_Y].size = sizeof(SANE_Int);
   ps->option[SOAP_OPTION_BR_Y].cap = SANE_CAP_SOFT_SELECT | SANE_CAP_SOFT_DETECT;
   ps->option[SOAP_OPTION_BR_Y].constraint_type = SANE_CONSTRAINT_RANGE;
   ps->option[SOAP_OPTION_BR_Y].constraint.range = &ps->bryRange;
   ps->bryRange.min = 0;
   ps->bryRange.quant = 0;

   return 0;
}

/* Verify current x/y extents and set effective extents. */ 
static int set_extents(struct soap_session *ps)
{
   int stat = 0;

   if ((ps->currentBrx > ps->currentTlx) && (ps->currentBrx - ps->currentTlx >= ps->minWidth) && (ps->currentBrx - ps->currentTlx <= ps->tlxRange.max))
   {
     ps->effectiveTlx = ps->currentTlx;
     ps->effectiveBrx = ps->currentBrx;
   }
   else
   {
     ps->effectiveTlx = 0;  /* current setting is not valid, zero it */
     ps->effectiveBrx = 0;
     stat = 1;
   }
   if ((ps->currentBry > ps->currentTly) && (ps->currentBry - ps->currentTly > ps->minHeight) && (ps->currentBry - ps->currentTly <= ps->tlyRange.max))
   {
     ps->effectiveTly = ps->currentTly;
     ps->effectiveBry = ps->currentBry;
   }
   else
   {
     ps->effectiveTly = 0;  /* current setting is not valid, zero it */
     ps->effectiveBry = 0;
     stat = 1;
   }
   return stat;
}

static int scan_start(struct soap_session *ps)
{
   char buf[2048];
   char footer[32];
   int milliInchWidth = (int)(SANE_UNFIX(ps->effectiveBrx - ps->effectiveTlx)/MM_PER_INCH*1000.0);
   int milliInchHeight = (int)(SANE_UNFIX(ps->effectiveBry - ps->effectiveTly)/MM_PER_INCH*1000.0);
   int milliInchXOffset = (int)(SANE_UNFIX(ps->effectiveTlx)/MM_PER_INCH*1000.0);
   int milliInchYOffset = (int)(SANE_UNFIX(ps->effectiveTly)/MM_PER_INCH*1000.0);
   int len, stat=1, footer_len, scan_mode;
   int media_width, media_height;

   if (http_open(ps->dd, HPMUD_S_SOAP_SCAN, &ps->http_handle) != HTTP_R_OK)
   {
      BUG("unable to open http connection %s\n", session->uri);
      goto bugout;
   }

   media_width = (int)(SANE_UNFIX(ps->tlxRange.max)/MM_PER_INCH*1000.0);
   media_height = (int)(SANE_UNFIX(ps->tlyRange.max)/MM_PER_INCH*1000.0);

   /* If Lineart map it to GRAY8 and let image processor do the transform to MONO. */
   scan_mode = ps->currentScanMode == CE_BLACK_AND_WHITE1 ? CE_GRAY8 : ps->currentScanMode;

   snprintf(ps->scan_id, sizeof(ps->scan_id), "scanjob %d", getpid()); 

   len = snprintf(buf, sizeof(buf), CREATE_SCAN_JOB_REQUEST, 
      ps->scan_id,
      sf_element[ps->currentCompression],                      /* <Format> */
      sf_compression[ps->currentCompression],                  /* <CompressionType> */
      ps->currentJpegQuality,                                  /* <JPEGQualityFactor> */
      ps->currentContrast,                                     /* <Contrast> (not used on O/H) */   
      milliInchXOffset,                                        /* <ScanRegionXOffset> */
      milliInchYOffset,                                        /* <ScanRegionYOffset> */
      milliInchWidth,                                          /* <ScanRegionWidth> */
      milliInchHeight,                                         /* <ScanRegionHeight> */
      ce_element[scan_mode],                                   /* <ColorProcessing> */
      ps->currentResolution, ps->currentResolution);           /* <Resolution> */

   DBG6("scan ticket: compression=%s xoffset=%d yoffset=%d width=%d height=%d mode=%s res=%d\n", sf_element[ps->currentCompression], 
	milliInchXOffset, milliInchYOffset, milliInchWidth, milliInchHeight, ce_element[ps->currentScanMode], ps->currentResolution);

   /* Write the http post header. Note do not send null termination byte. */
   if (http_write(ps->http_handle, POST_HEADER, sizeof(POST_HEADER)-1, EXCEPTION_TIMEOUT) != HTTP_R_OK)
   {
      BUG("unable to scan_start %s\n", ps->uri);
      goto bugout;
   }

   /* Write footer for xml payload. */
   footer_len = snprintf(footer, sizeof(footer), "%x\r\n", len);
   if (http_write(ps->http_handle, footer, footer_len, 1) != HTTP_R_OK)
   {
      BUG("unable to scan_start %s\n", ps->uri);
      goto bugout;
   }

   /* Write the xml payload. */
   if (http_write(ps->http_handle, buf, len, 1) != HTTP_R_OK)
   {
      BUG("unable to start_scan %s\n", ps->uri);
      goto bugout;
   }

   /* Write zero footer. */
   if (http_write(ps->http_handle, ZERO_FOOTER, sizeof(ZERO_FOOTER)-1, 1) != HTTP_R_OK)
   {
      BUG("unable to start_scan %s\n", ps->uri);
      goto bugout;
   }

   http_close(ps->http_handle);

   if (http_open(ps->dd, HPMUD_S_SOAP_SCAN, &ps->http_handle) != HTTP_R_OK)
   {
      BUG("unable to open http connection %s\n", session->uri);
      goto bugout;
   }

   stat=0;

bugout:
   if (stat && ps->http_handle)
   {
      http_close(ps->http_handle);   /* error, close http connection, otherwise leave it up for dime */
      ps->http_handle = 0;
   }

   return stat;
}

/*
 * SANE APIs.
 */

SANE_Status soap_open(SANE_String_Const device, SANE_Handle *handle)
{
   struct hpmud_model_attributes ma;
   struct device_platen *dp;
   int stat = SANE_STATUS_IO_ERROR, i, j;

   DBG8("sane_hpaio_open(%s)\n", device);

   if (session)
   {
      BUG("session in use\n");
      return SANE_STATUS_DEVICE_BUSY;
   }

   if ((session = create_session()) == NULL)
      return SANE_STATUS_NO_MEM;
    
   /* Set session to specified device. */
   snprintf(session->uri, sizeof(session->uri)-1, "hp:%s", device);   /* prepend "hp:" */

   /* Get actual model attributes from models.dat. */
   hpmud_query_model(session->uri, &ma);
   session->scantype = ma.scantype;

   if (hpmud_open_device(session->uri, ma.mfp_mode, &session->dd) != HPMUD_R_OK)
   {
      BUG("unable to open device %s\n", session->uri);
      goto bugout;

      free(session);
      session = NULL;
      return SANE_STATUS_IO_ERROR;
   }

   /* Get scanner elements from device. */
   if (get_scanner_elements(session, &session->elements))
   {
      BUG("unable to get_scanner_elements: uri=%s\n", session->uri);
      stat = SANE_STATUS_DEVICE_BUSY;
      goto bugout;
   }

   /* Init sane option descriptors. */
   init_options(session);  

   /* Determine supported Scan Modes and set sane option. */
   dp = &session->elements.config.platen;
   for(i=0, j=0; i<CE_MAX; i++)
   {
      if (dp->color[i] == CE_BLACK_AND_WHITE1)
      {
         session->scanModeList[j] = SANE_VALUE_SCAN_MODE_LINEART;
         session->scanModeMap[j++] = CE_BLACK_AND_WHITE1;
      }
      if (dp->color[i] == CE_GRAY8)
      {
         session->scanModeList[j] = SANE_VALUE_SCAN_MODE_GRAY;
         session->scanModeMap[j++] = CE_GRAY8;
      }
      if (dp->color[i] == CE_RGB24)
      {
         session->scanModeList[j] = SANE_VALUE_SCAN_MODE_COLOR;
         session->scanModeMap[j++] = CE_RGB24;
      }
   }
   soap_control_option(session, SOAP_OPTION_SCAN_MODE, SANE_ACTION_SET_AUTO, NULL, NULL); /* set default option */

   /* Set supported resolutions. */
   i=1;
   session->resolutionList[i++] = 75;
   session->resolutionList[i++] = 100;
   session->resolutionList[i++] = 150;
   session->resolutionList[i++] = 200;
   session->resolutionList[i++] = 300;
   session->resolutionList[i++] = 600;
   session->resolutionList[i++] = 1200;
   session->resolutionList[0] = i-1;    /* length of word_list */
   soap_control_option(session, SOAP_OPTION_SCAN_RESOLUTION, SANE_ACTION_SET_AUTO, NULL, NULL); /* set default option */

   /* Set supported contrast. */
   soap_control_option(session, SOAP_OPTION_CONTRAST, SANE_ACTION_SET_AUTO, NULL, NULL); /* set default option */

   /* Set supported compression. (Note, cm1017 may say it supports MMR, but it doesn't) */
   soap_control_option(session, SOAP_OPTION_COMPRESSION, SANE_ACTION_SET_AUTO, NULL, NULL); /* set default option */
   
   /* Determine if jpeg quality factor is supported and set sane option. */
   if (session->elements.config.settings.jpeg_quality_factor_supported)
      session->option[SOAP_OPTION_JPEG_QUALITY].cap &= ~SANE_CAP_INACTIVE; 
   else
      session->option[SOAP_OPTION_JPEG_QUALITY].cap |= SANE_CAP_INACTIVE; 
   soap_control_option(session, SOAP_OPTION_JPEG_QUALITY, SANE_ACTION_SET_AUTO, NULL, NULL); /* set default option */

   /* Set x,y extents. */
   session->minWidth = SANE_FIX(session->elements.config.platen.minimum_size.width/1000.0*MM_PER_INCH);
   session->minHeight = SANE_FIX(session->elements.config.platen.minimum_size.height/1000.0*MM_PER_INCH);
   session->tlxRange.max = SANE_FIX(session->elements.config.platen.maximum_size.width/1000.0*MM_PER_INCH);
   session->brxRange.max = session->tlxRange.max;
   session->tlyRange.max = SANE_FIX(session->elements.config.platen.maximum_size.height/1000.0*MM_PER_INCH);
   session->bryRange.max = session->tlyRange.max;
   soap_control_option(session, SOAP_OPTION_TL_X, SANE_ACTION_SET_AUTO, NULL, NULL); /* set default option */
   soap_control_option(session, SOAP_OPTION_TL_Y, SANE_ACTION_SET_AUTO, NULL, NULL); /* set default option */
   soap_control_option(session, SOAP_OPTION_BR_X, SANE_ACTION_SET_AUTO, NULL, NULL); /* set default option */
   soap_control_option(session, SOAP_OPTION_BR_Y, SANE_ACTION_SET_AUTO, NULL, NULL); /* set default option */

   *handle = (SANE_Handle *)session;

   stat = SANE_STATUS_GOOD;

bugout:

   if (stat != SANE_STATUS_GOOD)
   {
      if (session)
      {
         if (session->dd > 0)
            hpmud_close_device(session->dd);
         free(session);
         session = NULL;
      }
   }

   return stat;
}

void soap_close(SANE_Handle handle)
{
   struct soap_session *ps = (struct soap_session *)handle;

   DBG8("sane_hpaio_close()\n"); 

   if (ps == NULL || ps != session)
   {
      BUG("invalid sane_close\n");
      return;
   }

   if (ps->dd > 0)
      hpmud_close_device(ps->dd);
    
   free(ps);
   session = NULL;
}

const SANE_Option_Descriptor *soap_get_option_descriptor(SANE_Handle handle, SANE_Int option)
{
   struct soap_session *ps = (struct soap_session *)handle;

   DBG8("sane_hpaio_get_option_descriptor(option=%s)\n", ps->option[option].name);

   if (option < 0 || option >= SOAP_OPTION_MAX)
      return NULL;

   return &ps->option[option];
}

SANE_Status soap_control_option(SANE_Handle handle, SANE_Int option, SANE_Action action, void *value, SANE_Int *set_result)
{
   struct soap_session *ps = (struct soap_session *)handle;
   SANE_Int *int_value = value, mset_result=0;
   int i, stat=SANE_STATUS_INVAL;
   char sz[64];

   switch(option)
   {
      case SOAP_OPTION_COUNT:
         if (action == SANE_ACTION_GET_VALUE)
         {
            *int_value = SOAP_OPTION_MAX;
            stat = SANE_STATUS_GOOD;
         }
         break;
      case SOAP_OPTION_SCAN_MODE:
         if (action == SANE_ACTION_GET_VALUE)
         {
            for (i=0; ps->scanModeList[i]; i++)
            {
               if (ps->currentScanMode == ps->scanModeMap[i])
               {
                  strcpy(value, ps->scanModeList[i]);
                  stat = SANE_STATUS_GOOD;
                  break;
               }
            }
         }
         else if (action == SANE_ACTION_SET_VALUE)
         {
            for (i=0; ps->scanModeList[i]; i++)
            {
               if (strcmp(ps->scanModeList[i], value) == 0)
               {
                  ps->currentScanMode = ps->scanModeMap[i];
                  set_scan_mode_side_effects(ps, ps->currentScanMode);
                  mset_result |= SANE_INFO_RELOAD_PARAMS | SANE_INFO_RELOAD_OPTIONS;
                  stat = SANE_STATUS_GOOD;
                  break;
               }
            }
         }
         else
         {  /* Set default. */
            ps->currentScanMode = CE_RGB24;
            set_scan_mode_side_effects(ps, ps->currentScanMode);
            stat = SANE_STATUS_GOOD;
         }
         break;
      case SOAP_OPTION_SCAN_RESOLUTION:
         if (action == SANE_ACTION_GET_VALUE)
         {
            *int_value = ps->currentResolution;
            stat = SANE_STATUS_GOOD;
         }
         else if (action == SANE_ACTION_SET_VALUE)
         {
            for (i=1; i <= ps->resolutionList[0]; i++)
            {
               if (ps->resolutionList[i] == *int_value)
               {
                  ps->currentResolution = *int_value;
                  mset_result |= SANE_INFO_RELOAD_PARAMS;
                  stat = SANE_STATUS_GOOD;
                  break;
               }
            }
         }
         else
         {  /* Set default. */
            ps->currentResolution = 75;
            stat = SANE_STATUS_GOOD;
         }
         break;
      case SOAP_OPTION_CONTRAST:
         if (action == SANE_ACTION_GET_VALUE)
         {
            *int_value = ps->currentContrast;
            stat = SANE_STATUS_GOOD;
         }
         else if (action == SANE_ACTION_SET_VALUE)
         {
            if (*int_value >= SOAP_CONTRAST_MIN && *int_value <= SOAP_CONTRAST_MAX)
            {
               ps->currentContrast = *int_value;
               stat = SANE_STATUS_GOOD;
               break;
            }
         }
         else
         {  /* Set default. */
            ps->currentContrast = SOAP_CONTRAST_DEFAULT;
            stat = SANE_STATUS_GOOD;
         }
         break;
      case SOAP_OPTION_COMPRESSION:
         if (action == SANE_ACTION_GET_VALUE)
         {
            for (i=0; ps->compressionList[i]; i++)
            {
               if (ps->currentCompression == ps->compressionMap[i])
               {
                  strcpy(value, ps->compressionList[i]);
                  stat = SANE_STATUS_GOOD;
                  break;
               }
            }
         }
         else if (action == SANE_ACTION_SET_VALUE)
         {
            for (i=0; ps->compressionList[i]; i++)
            {
               if (strcmp(ps->compressionList[i], value) == 0)
               {
                  ps->currentCompression = ps->compressionMap[i];
                  stat = SANE_STATUS_GOOD;
                  break;
               }
            }
         }
         else
         {  /* Set default. */
            ps->currentCompression = SF_JFIF;
            stat = SANE_STATUS_GOOD;
         }
         break;
      case SOAP_OPTION_JPEG_QUALITY:
         if (action == SANE_ACTION_GET_VALUE)
         {
            *int_value = ps->currentJpegQuality;
            stat = SANE_STATUS_GOOD;
         }
         else if (action == SANE_ACTION_SET_VALUE)
         {
            if (*int_value >= MIN_JPEG_COMPRESSION_FACTOR && *int_value <= MAX_JPEG_COMPRESSION_FACTOR)
            {
               ps->currentJpegQuality = *int_value;
               stat = SANE_STATUS_GOOD;
               break;
            }
         }
         else
         {  /* Set default. */
            ps->currentJpegQuality = SAFER_JPEG_COMPRESSION_FACTOR;
            stat = SANE_STATUS_GOOD;
         }
         break;
      case SOAP_OPTION_TL_X:
         if (action == SANE_ACTION_GET_VALUE)
         {
            *int_value = ps->currentTlx;
            stat = SANE_STATUS_GOOD;
         }
         else if (action == SANE_ACTION_SET_VALUE)
         {
            if (*int_value >= ps->tlxRange.min && *int_value <= ps->tlxRange.max)
            {
               ps->currentTlx = *int_value;
               mset_result |= SANE_INFO_RELOAD_PARAMS;
               stat = SANE_STATUS_GOOD;
               break;
            }
         }
         else
         {  /* Set default. */
            ps->currentTlx = ps->tlxRange.min;
            stat = SANE_STATUS_GOOD;
         }
         break;
      case SOAP_OPTION_TL_Y:
         if (action == SANE_ACTION_GET_VALUE)
         {
            *int_value = ps->currentTly;
            stat = SANE_STATUS_GOOD;
         }
         else if (action == SANE_ACTION_SET_VALUE)
         {
            if (*int_value >= ps->tlyRange.min && *int_value <= ps->tlyRange.max)
            {
               
               ps->currentTly = *int_value;
               mset_result |= SANE_INFO_RELOAD_PARAMS;
               stat = SANE_STATUS_GOOD;
               break;
            }
         }
         else
         {  /* Set default. */
            ps->currentTly = ps->tlyRange.min;
            stat = SANE_STATUS_GOOD;
         }
         break;
      case SOAP_OPTION_BR_X:
         if (action == SANE_ACTION_GET_VALUE)
         {
            *int_value = ps->currentBrx;
            stat = SANE_STATUS_GOOD;
         }
         else if (action == SANE_ACTION_SET_VALUE)
         {
            if (*int_value >= ps->brxRange.min && *int_value <= ps->brxRange.max)
            {
               ps->currentBrx = *int_value;
               mset_result |= SANE_INFO_RELOAD_PARAMS;
               stat = SANE_STATUS_GOOD;
               break;
            }
         }
         else
         {  /* Set default. */
            ps->currentBrx = ps->brxRange.max;
            stat = SANE_STATUS_GOOD;
         }
         break;
      case SOAP_OPTION_BR_Y:
         if (action == SANE_ACTION_GET_VALUE)
         {
            *int_value = ps->currentBry;
            stat = SANE_STATUS_GOOD;
         }
         else if (action == SANE_ACTION_SET_VALUE)
         {
            if (*int_value >= ps->bryRange.min && *int_value <= ps->bryRange.max)
            {
               ps->currentBry = *int_value;
               mset_result |= SANE_INFO_RELOAD_PARAMS;
               stat = SANE_STATUS_GOOD;
               break;
            }
         }
         else
         {  /* Set default. */
            ps->currentBry = ps->bryRange.max;
            stat = SANE_STATUS_GOOD;
         }
         break;
      default:
         break;
   }

   if (set_result)
      *set_result = mset_result;

   if (stat != SANE_STATUS_GOOD)
   {
      BUG("control_option failed: option=%s action=%s\n", ps->option[option].name, 
                  action==SANE_ACTION_GET_VALUE ? "get" : action==SANE_ACTION_SET_VALUE ? "set" : "auto");
   }

   DBG8("sane_hpaio_control_option (option=%s action=%s value=%s)\n", ps->option[option].name, 
                        action==SANE_ACTION_GET_VALUE ? "get" : action==SANE_ACTION_SET_VALUE ? "set" : "auto",
     value ? ps->option[option].type == SANE_TYPE_STRING ? (char *)value : psnprintf(sz, sizeof(sz), "%d", *(int *)value) : "na");

   return stat;
}

SANE_Status soap_get_parameters(SANE_Handle handle, SANE_Parameters *params)
{
   struct soap_session *ps = (struct soap_session *)handle;

   set_extents(ps);

   scan_parameters(ps, params, ps->ipHandle ? 1 : 0);

   DBG8("sane_hpaio_get_parameters(): format=%d, last_frame=%d, lines=%d, depth=%d, pixels_per_line=%d, bytes_per_line=%d\n",
                    params->format, params->last_frame, params->lines, params->depth, params->pixels_per_line, params->bytes_per_line);

   return SANE_STATUS_GOOD;
}

SANE_Status soap_start(SANE_Handle handle)
{
   struct soap_session *ps = (struct soap_session *)handle;
   SANE_Parameters pp;
   IP_IMAGE_TRAITS traits;
   IP_XFORM_SPEC xforms[IP_MAX_XFORMS], *pXform=xforms;
   int stat, ret;

   DBG8("sane_hpaio_start()\n");

   if (set_extents(ps))
   {
      BUG("invalid extents: tlx=%d brx=%d tly=%d bry=%d minwidth=%d minheight%d maxwidth=%d maxheight=%d\n",
         ps->currentTlx, ps->currentTly, ps->currentBrx, ps->currentBry, ps->minWidth, ps->minHeight, ps->tlxRange.max, ps->tlyRange.max);
      stat = SANE_STATUS_INVAL;
      goto bugout;
   }   

   /* Get current scanner state. */
   if (get_scanner_elements(ps, &ps->elements))
   {
      stat = SANE_STATUS_IO_ERROR;
      goto bugout;
   }

   /* If input is ADF and ADF is empty, return SANE_STATUS_NO_DOCS. */

   /* Make sure scanner is idle. */
   if (ps->elements.status.state != SS_IDLE)
   {
      BUG("scanner is not idle: state=%d reason=%d\n", ps->elements.status.state, ps->elements.status.reason);
      stat = SANE_STATUS_DEVICE_BUSY;
      goto bugout;
   }

   /* Start scan and get actual image traits. */
   if (scan_start(ps))
   {
      stat = SANE_STATUS_IO_ERROR;
      goto bugout;
   }

   memset(xforms, 0, sizeof(xforms));    

   /* Setup image-processing pipeline for xform. */
   if (ps->currentScanMode == CE_RGB24 || ps->currentScanMode == CE_GRAY8)
   {
      switch(ps->currentCompression)
      {
         case SF_JFIF:
            pXform->aXformInfo[IP_JPG_DECODE_FROM_DENALI].dword = 0;    /* 0=no */
            ADD_XFORM(X_JPG_DECODE);
            pXform->aXformInfo[IP_CNV_COLOR_SPACE_WHICH_CNV].dword = IP_CNV_YCC_TO_SRGB;
            pXform->aXformInfo[IP_CNV_COLOR_SPACE_GAMMA].dword = 0x00010000;
            ADD_XFORM(X_CNV_COLOR_SPACE);
            break;
         case SF_HPRAW:
         default:
            break;
      }
   }
   else
   {  /* Must be BLACK_AND_WHITE1 (Lineart). */
      switch(ps->currentCompression)
      {
         case SF_JFIF:
            pXform->aXformInfo[IP_JPG_DECODE_FROM_DENALI].dword = 0;    /* 0=no */
            ADD_XFORM(X_JPG_DECODE);
            pXform->aXformInfo[IP_GRAY_2_BI_THRESHOLD].dword = 127;
            ADD_XFORM(X_GRAY_2_BI);
            break;
         case SF_HPRAW:
            pXform->aXformInfo[IP_GRAY_2_BI_THRESHOLD].dword = 127;
            ADD_XFORM(X_GRAY_2_BI);
         default:
            break;
      }
   }

   /* Setup x/y cropping for xform. (Actually we let cm1017 do it's own cropping) */
   pXform->aXformInfo[IP_CROP_LEFT].dword = 0;
   pXform->aXformInfo[IP_CROP_RIGHT].dword = 0;
   pXform->aXformInfo[IP_CROP_TOP].dword = 0;
   pXform->aXformInfo[IP_CROP_MAXOUTROWS].dword = 0;
   ADD_XFORM(X_CROP);

   /* Setup x/y padding for xform. (Actually we let cm1017 do it's own padding) */
   pXform->aXformInfo[IP_PAD_LEFT].dword = 0; /* # of pixels to add to left side */
   pXform->aXformInfo[IP_PAD_RIGHT].dword = 0; /* # of pixels to add to right side */
   pXform->aXformInfo[IP_PAD_TOP].dword = 0; /* # of rows to add to top */
   pXform->aXformInfo[IP_PAD_BOTTOM].dword = 0;  /* # of rows to add to bottom */
   pXform->aXformInfo[IP_PAD_VALUE].dword = ps->currentScanMode == CE_BLACK_AND_WHITE1 ? 0 : -1;   /* lineart white = 0, rgb white = -1 */ 
   pXform->aXformInfo[IP_PAD_MIN_HEIGHT].dword = 0;
   ADD_XFORM(X_PAD);

   /* Open image processor. */
   if ((ret = ipOpen(pXform-xforms, xforms, 0, &ps->ipHandle)) != IP_DONE)
   {
      BUG("unable open image processor: err=%d\n", ret);
      stat = SANE_STATUS_INVAL;
      goto bugout;
   }

   /* Set known input image attributes. */
   scan_parameters(ps, &pp, 0);
   traits.iPixelsPerRow = pp.pixels_per_line;
   switch(ps->currentScanMode)
   {
      case CE_BLACK_AND_WHITE1:         /* lineart */
      case CE_GRAY8:
         traits.iBitsPerPixel = 8;     /* grayscale */
         break;
      case CE_RGB24:
      default:
         traits.iBitsPerPixel = 24;      /* color */
         break;
   }
   traits.lHorizDPI = ps->currentResolution << 16;
   traits.lVertDPI = ps->currentResolution << 16;
   traits.lNumRows =  pp.lines;
   traits.iNumPages = 1;
   traits.iPageNum = 1;
   traits.iComponentsPerPixel = ((traits.iBitsPerPixel % 3) ? 1 : 3);
   ipSetDefaultInputTraits(ps->ipHandle, &traits);

   if (dime_open(ps->http_handle, &ps->dime_handle) != DIME_R_OK)
   {
      BUG("unable to start dime document: %s\n", session->uri);
      stat = SANE_STATUS_IO_ERROR;
      goto bugout;
   }

   /* Get output image attributes from the image processor. */
   if (ps->currentCompression == SF_JFIF)
   {
      /* Enable parsed header flag. */
      ipResultMask(ps->ipHandle, IP_PARSED_HEADER);

      /* Wait for image processor to process header so we know the exact size of the image for sane_get_params. */
      while (1)
      {
         ret = get_ip_data(ps, NULL, 0, NULL);

         if (ret & (IP_INPUT_ERROR | IP_FATAL_ERROR | IP_DONE))
         {
            BUG("ipConvert error=%x\n", ret);
            stat = SANE_STATUS_IO_ERROR;
            goto bugout;
         }

         if (ret & IP_PARSED_HEADER)
         {
            ipGetImageTraits(ps->ipHandle, NULL, &ps->imageTraits);  /* get valid image traits */
            ipResultMask(ps->ipHandle, 0);                          /* disable parsed header flag */
            break;
         }
      }
   }
   else
      ipGetImageTraits(ps->ipHandle, NULL, &ps->imageTraits);  /* get valid image traits */

   stat = SANE_STATUS_GOOD;

bugout:
   if (stat != SANE_STATUS_GOOD)
   {
      if (ps->ipHandle)
      {
         ipClose(ps->ipHandle); 
         ps->ipHandle = 0;
      }   
      if (ps->dime_handle)
      {
         dime_close(ps->dime_handle); 
         ps->dime_handle = 0;
      } 
      if (ps->http_handle)
      {
         http_close(ps->http_handle);
         ps->http_handle = 0;
      }
   }

   return stat;
}

SANE_Status soap_read(SANE_Handle handle, SANE_Byte *data, SANE_Int maxLength, SANE_Int *length)
{
   struct soap_session *ps = (struct soap_session *)handle;
   int ret, stat=SANE_STATUS_IO_ERROR;

   DBG8("sane_hpaio_read() handle=%p data=%p maxLength=%d\n", (void *)handle, data, maxLength);

   ret = get_ip_data(ps, data, maxLength, length);

   if(ret & (IP_INPUT_ERROR | IP_FATAL_ERROR))
   {
      BUG("ipConvert error=%x\n", ret);
      goto bugout;
   }

   if (ret & IP_DONE)
      stat = SANE_STATUS_EOF;
   else
      stat = SANE_STATUS_GOOD;

bugout:
   if (stat != SANE_STATUS_GOOD)
   {
      if (ps->ipHandle)
      {
         /* Note always call ipClose when SANE_STATUS_EOF, do not depend on sane_cancel because sane_cancel is only called at the end of a batch job. */ 
         ipClose(ps->ipHandle);  
         ps->ipHandle = 0;
      } 
      if (ps->dime_handle)
      {
         dime_close(ps->dime_handle);
         ps->dime_handle = 0;
      }  
      if (ps->http_handle)
      {
         http_close(ps->http_handle);
         ps->http_handle = 0;
      }
   }

   DBG8("-sane_hpaio_read() output=%p bytes_read=%d maxLength=%d status=%d\n", data, *length, maxLength, stat);

   return stat;
}

void soap_cancel(SANE_Handle handle)
{
   struct soap_session *ps = (struct soap_session *)handle;

   DBG8("sane_hpaio_cancel()\n"); 

   /*
    * Sane_cancel is always called at the end of the scan job. Note that on a multiple page scan job 
    * sane_cancel is called only once.
    */

   if (ps->ipHandle)
   {
      ipClose(ps->ipHandle); 
      ps->ipHandle = 0;
   }

   if (ps->dime_handle)
   {
      dime_close(ps->dime_handle);
      ps->dime_handle = 0;
   }  

   if (ps->http_handle)
   {
      http_close(ps->http_handle);
      ps->http_handle = 0;
   }

   cancel_job(ps);
}

