/************************************************************************************\
  bb_ledm.c - HP SANE backend support for ledm based multi-function peripherals
  (c) 2010 Copyright Hewlett-Packard Development Company, LP

  Primary Author: Naga Samrat Chowdary, Narla
  Contributing Authors: Yashwant Kumar Sahu
\************************************************************************************/

# ifndef _GNU_SOURCE
# define _GNU_SOURCE
# endif

# include <stdarg.h>
# include <syslog.h>
# include <stdio.h>
# include <string.h>
# include <fcntl.h>
# include <math.h>
# include "sane.h"
# include "saneopts.h"
# include "hpmud.h"
# include "hpip.h"
# include "common.h"
# include "ledm.h"
# include "ledmi.h"
# include "http.h"
# include "xml.h"
# include <stdlib.h>

# include <stdint.h>

# define _STRINGIZE(x) #x
# define STRINGIZE(x) _STRINGIZE(x)

# define _BUG(args...) syslog(LOG_ERR, __FILE__ " " STRINGIZE(__LINE__) ": " args)

# ifdef BB_LEDM_DEBUG
   # define _DBG(args...) syslog(LOG_INFO, __FILE__ " " STRINGIZE(__LINE__) ": " args)
# else
   # define _DBG(args...)
# endif

enum DOCUMENT_TYPE
{
  DT_AUTO = 1,
  DT_MAX,
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
  int width;         			       /* in 1/1000 of an inch */
  int height;        			       /* in 1/1000 of an inch */
};

struct device_settings
{
  enum COLOR_ENTRY color[CE_MAX];
  enum SCAN_FORMAT formats[SF_MAX];
  int jpeg_quality_factor_supported;           /* 0=false, 1=true */
  enum DOCUMENT_TYPE docs[DT_MAX];
  int document_size_auto_detect_supported;     /* 0=false, 1=true */
  int feeder_capacity;
  int rotation;                                /* needed adf front side image rotation */
  int duplex_rotation;                         /* needed adf back side image rotation */
};

struct device_platen
{
  int flatbed_supported;                       /* 0=false, 1=true */
  struct media_size minimum_size;
  struct media_size maximum_size;
  struct media_size optical_resolution;
  int platen_resolution_list[MAX_LIST_SIZE];
};

struct device_adf
{
  int supported;                               /* 0=false, 1=true */
  int duplex_supported;                        /* 0=false, 1=true */
  struct media_size minimum_size;
  struct media_size maximum_size;
  struct media_size optical_resolution;
  int adf_resolution_list[MAX_LIST_SIZE];
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
  int paper_in_adf;                            /* 0=false, 1=true */
  int scan_to_available;                       /* 0=false, 1=true */
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
  int lines;                                   /* number of lines */
  int bytes_per_line;                          /* zero if jpeg */
  enum SCAN_FORMAT format;
  int jpeg_quality_factor;
  int images_to_transfer;                      /* number of images to scan */
  enum INPUT_SOURCE source;
  enum DOCUMENT_TYPE doc;
  struct media_size input_size;
  int scan_region_xoffset;
  int scan_region_yoffset;
  int scan_region_width;
  int scan_region_height;
  enum COLOR_ENTRY color;
  struct media_size resolution;
};

struct bb_ledm_session
{
  struct wscn_create_scan_job_response job;    /* actual scan job attributes (valid after sane_start) */
  struct wscn_scan_elements elements;          /* scanner elements (valid after sane_open and sane_start) */
  HTTP_HANDLE http_handle;
};

/* Following elements must match their associated enum table. */
static const char *sf_element[SF_MAX] = { "", "raw", "jpeg" };  /* SCAN_FORMAT (compression) */
static const char *ce_element[CE_MAX] = { "", "K1", "Gray8", "Color8" };   /* COLOR_ENTRY */
static const char *is_element[IS_MAX] = { "", "Platen", "Adf", "ADFDuplex" };   /* INPUT_SOURCE */

# define POST_HEADER "POST /Scan/Jobs HTTP/1.1\r\nHost: 16.180.119.199:8080\r\nUser-Agent: \
hp\r\nAccept: text/plain, */*\r\nAccept-Language: en-us,en;q=0.5\r\n\
Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7\r\nKeep-Alive: 1000\r\nProxy-Connection: keep-alive\r\n\
Content-Type: */*; charset=UTF-8\r\nX-Requested-With: XMLHttpRequest\r\n\
Referer: http://16.180.119.199:8080/\r\nContent-Length: 890\r\nCookie: AccessCounter=new\r\n\
Pragma: no-cache\r\nCache-Control: no-cache\r\n\r\n" 

# define GET_SCANNER_ELEMENTS "GET /Scan/ScanCaps HTTP/1.1\r\n\
Host: localhost\r\nUser-Agent: hplip\r\n\
Accept: text/xml\r\n\
Accept-Language: en-us,en\r\n\
Accept-Charset:utf-8\r\n\
Keep-Alive: 20\r\nProxy-Connection: keep-alive\r\nCookie: AccessCounter=new\r\n0\r\n\r\n"

# define GET_SCANNER_STATUS "GET /Scan/Status HTTP/1.1\r\n\
Host: localhost\r\nUser-Agent: hplip\r\n\
Accept: text/xml\r\n\
Accept-Language: en-us,en\r\n\
Accept-Charset:utf-8\r\n\
Keep-Alive: 20\r\nProxy-Connection: keep-alive\r\nCookie: AccessCounter=new\r\n0\r\n\r\n"

# define CREATE_SCAN_JOB_REQUEST "<scan:ScanJob xmlns:scan=\"http://www.hp.com/schemas/imaging/con/cnx/scan/2008/08/19\" xmlns:dd=\"http://www.hp.com/schemas/imaging/con/dictionaries/1.0/\">\
<scan:XResolution>%d</scan:XResolution>\
<scan:YResolution>%d</scan:YResolution>\
<scan:XStart>%d</scan:XStart>\
<scan:YStart>%d</scan:YStart>\
<scan:Width>%d</scan:Width>\
<scan:Height>%d</scan:Height>\
<scan:Format>%s</scan:Format>\
<scan:CompressionQFactor>15</scan:CompressionQFactor>\
<scan:ColorSpace>%s</scan:ColorSpace>\
<scan:BitDepth>%d</scan:BitDepth>\
<scan:InputSource>%s</scan:InputSource>\
<scan:AdfOptions>SelectSinglePage</scan:AdfOptions>\
<scan:GrayRendering>NTSC</scan:GrayRendering>\
<scan:ToneMap>\
<scan:Gamma>0</scan:Gamma>\
<scan:Brightness>1000</scan:Brightness>\
<scan:Contrast>1000</scan:Contrast>\
<scan:Highlite>0</scan:Highlite>\
<scan:Shadow>0</scan:Shadow></scan:ToneMap>\
<scan:ContentType>Photo</scan:ContentType></scan:ScanJob>" 

# define CANCEL_JOB_REQUEST "PUT %s HTTP/1.1\r\nHost: localhost\r\nUser-Agent: hp\r\n\
Accept: text/plain\r\nAccept-Language: en-us,en\r\nAccept-Charset:utf-8\r\nKeep-Alive: 10\r\n\
Content-Type: text/xml\r\nProxy-Connection: Keep-alive\r\nX-Requested-With: XMLHttpRequest\r\nReferer: localhost\r\n\
Content-Length: 523\r\nCookie: AccessCounter=new\r\n\r\n\
<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n\
<!-- THIS DATA SUBJECT TO DISCLAIMER(S) INCLUDED WITH THE PRODUCT OF ORIGIN. -->\n\
<j:Job xmlns:j=\"http://www.hp.com/schemas/imaging/con/ledm/jobs/2009/04/30\" \
xmlns:dd=\"http://www.hp.com/schemas/imaging/con/dictionaries/1.0/\" \
xmlns:fax=\"http://www.hp.com/schemas/imaging/con/fax/2008/06/13\" \
xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" \
xsi:schemaLocation=\"http://www.hp.com/schemas/imaging/con/ledm/jobs/2009/04/30 ../schemas/Jobs.xsd\">\
<j:JobState>Canceled</j:JobState></j:Job>"

# define ZERO_FOOTER "\r\n0\r\n\r\n"

static int parse_scan_elements(const char *payload, int size, struct wscn_scan_elements *elements)
{
  char tag[512];
  char value[128];
  int i;
  char *tail=(char *)payload;

  memset(elements, 0, sizeof(struct wscn_scan_elements));

  while (1)
  {
    get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);

    if (!tag[0])
      break;     /* done */

    if(strncmp(tag, "ColorEntries", 12) == 0)
    {
      int h=1;
      while(h)
      {
        get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
        if(strncmp(tag, "Platen", 6) ==0) break;
        if(strncmp(tag, "/ColorEntries", 13) ==0) break;
        if(strncmp(tag, "ColorType", 9)==0)
        {
          get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
          if (strcmp(value, ce_element[CE_K1]) == 0)
            elements->config.settings.color[CE_K1] = CE_K1;
          else if (strcmp(value, ce_element[CE_GRAY8]) == 0)
             elements->config.settings.color[CE_GRAY8] = CE_GRAY8;
          else if (strcmp(value, ce_element[CE_COLOR8]) == 0)
             elements->config.settings.color[CE_COLOR8] = CE_COLOR8;
//        else
//           _BUG("unknowned element=%s, sf_element[SF_JPEG]=%s, sf_element[SF_RAW]=%s\n", value, sf_element[SF_JPEG], sf_element[SF_RAW] );
          _DBG("FormatSupported:%s\n", value);
          get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
          if(strncmp(tag, "/ColorEntries", 13) == 0) h=0; 
         }
         if(strncmp(tag, "/ColorEntries", 13) == 0) h=0; 
       }   
    }         

    if(strncmp(tag, "Platen", 6) == 0)
    {
      elements->config.platen.flatbed_supported = 1;
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
      elements->config.platen.minimum_size.width=strtol(value, NULL, 10);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
      elements->config.platen.minimum_size.height=strtol(value, NULL, 10);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
      elements->config.platen.maximum_size.width=strtol(value, NULL, 10);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
      elements->config.platen.maximum_size.height=strtol(value, NULL, 10);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
      elements->config.platen.optical_resolution.width=strtol(value, NULL, 10);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
      elements->config.platen.optical_resolution.height=strtol(value, NULL, 10);        
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_element(tail, size-(tail-payload), value, sizeof(value), &tail);

      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      i=1; 
      elements->config.platen.platen_resolution_list[0]=0;
      while(strcmp(tag, "/SupportedResolutions"))
      {
        get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
        if(!strcmp(tag, "Resolution"))
        {
          get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
          get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
          if(strtol(value, NULL, 10) && elements->config.platen.platen_resolution_list[i-1] != strtol(value, NULL, 10))
            elements->config.platen.platen_resolution_list[i++]=strtol(value, NULL, 10);
        }
      }
      elements->config.platen.platen_resolution_list[0]=i-1;
    }

    if(strncmp(tag, "Adf", 3) == 0 && strlen(tag) == 3)
    {
      elements->config.adf.supported = 1;
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
      elements->config.adf.minimum_size.width=strtol(value, NULL, 10);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
      elements->config.adf.minimum_size.height=strtol(value, NULL, 10);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
      elements->config.adf.maximum_size.width=strtol(value, NULL, 10);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
      elements->config.adf.maximum_size.height=strtol(value, NULL, 10);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
      elements->config.adf.optical_resolution.width=strtol(value, NULL, 10);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
      elements->config.adf.optical_resolution.height=strtol(value, NULL, 10);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_element(tail, size-(tail-payload), value, sizeof(value), &tail);

      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
      i=1; 
      elements->config.adf.adf_resolution_list[0]=0;
      while(strcmp(tag, "/SupportedResolutions"))
      {
        get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
        if(!strcmp(tag, "Resolution"))
        {
          get_tag(tail, size-(tail-payload), tag, sizeof(tag), &tail);
          get_element(tail, size-(tail-payload), value, sizeof(value), &tail);
          if(strtol(value, NULL, 10) && elements->config.adf.adf_resolution_list[i-1] != strtol(value, NULL, 10))
            elements->config.adf.adf_resolution_list[i++]=strtol(value, NULL, 10);
        }
      }
    elements->config.adf.adf_resolution_list[0]=i-1;
    }
  }  /* end while (1) */
  return 0;
} /* parse_scan_elements */

static struct bb_ledm_session* create_session()
{
  struct bb_ledm_session* pbb;

  if ((pbb = malloc(sizeof(struct bb_ledm_session))) == NULL)
  {
    return NULL;
  }

  memset(pbb, 0, sizeof(struct bb_ledm_session));
  return pbb;
} /* create_session */

static int read_http_payload(struct ledm_session *ps, char *payload, int max_size, int sec_timeout, int *bytes_read)
{
  struct bb_ledm_session *pbb = ps->bb_session;
  int stat=1, total=0, len;
  int tmo=sec_timeout;
  enum HTTP_RESULT ret;
  int payload_length=-1;
  char *temp=NULL;

  *bytes_read = 0;

  if(http_read_header(pbb->http_handle, payload, max_size, tmo, &len) != HTTP_R_OK)
      goto bugout;

  temp=strstr(payload, "Content-Length:");
  temp=strtok(temp, "\r\n");
  temp=temp+16;
  payload_length=strtol(temp, NULL, 10);

  memset(payload, ' ', len);
  len=payload_length;

  if(payload_length==-1)
  {
    len=1000;
    int i=10;
    while(i){
    ret = http_read(pbb->http_handle, payload+total, max_size-total, tmo, &len);
    i--;}
  }
  else{
    while (total < payload_length) {
      ret = http_read(pbb->http_handle, payload+total, max_size-total, tmo, &len);
     if (ret == HTTP_R_EOF)
         break;    /* done */

      if (!(ret == HTTP_R_OK || ret == HTTP_R_EOF))
         goto bugout;
      total+=len;
      tmo=1;
}
*bytes_read = total;
stat=0;
}
bugout:
   return stat;
} /* read_http_payload */

void parser(char *buffer)
{
  char *temp=buffer;
  char *p=buffer;
  int b=2;

  while(b)
  {
    if(*p == '>') b--;
    p++; 
  }

  while(*p) 
  {
    if(*p == '\r' || *p == '\n' || *p == '\t') p++;
    else 
    { 
      *temp = *p;
      temp ++;
      p++; 
    }
  }
  *temp='\0';
}

static int get_scanner_elements(struct ledm_session *ps, struct wscn_scan_elements *elements)
{
  struct bb_ledm_session *pbb = ps->bb_session;
  int bytes_read;
  int stat=1, tmo=EXCEPTION_TIMEOUT;
  char buf[8192];

  if (http_open(ps->dd, HPMUD_S_LEDM_SCAN, &pbb->http_handle) != HTTP_R_OK)
  {
    _BUG("unable to open http connection %s\n", ps->uri);
    goto bugout;
  }

  /* Write the xml payload. */
  if (http_write(pbb->http_handle, GET_SCANNER_ELEMENTS, sizeof(GET_SCANNER_ELEMENTS)-1, tmo) != HTTP_R_OK)
  {
    _BUG("unable to get_scanner_elements %s\n", ps->uri);
    goto bugout;
  }

  /* Read http response. */
  if (read_http_payload(ps, buf, sizeof(buf), tmo, &bytes_read))
    goto bugout;

  parser(buf);

  bytes_read=strlen(buf)+1;

  parse_scan_elements(buf, bytes_read, elements);
  stat=0;

bugout:
  if (pbb->http_handle)
  {
    http_close(pbb->http_handle);
    pbb->http_handle = 0;
  }
  return stat;
} /* get_scanner_elements */

static int cancel_job(struct ledm_session *ps)
{
  struct bb_ledm_session *pbb = ps->bb_session;
  int len, stat=1, tmo=EXCEPTION_TIMEOUT;
  char buf[2048];
  int bytes_read;

  if (http_open(ps->dd, HPMUD_S_LEDM_SCAN, &pbb->http_handle) != HTTP_R_OK)
  {
    _BUG("unable to open http connection %s\n", ps->uri);
    goto bugout;
  }

  len = snprintf(buf, sizeof(buf), CANCEL_JOB_REQUEST, ps->url);

  if (http_write(pbb->http_handle, buf, len, 1) != HTTP_R_OK)
  {
    _BUG("unable to cancel_job %s\n", ps->url);
//    goto bugout;
  }

  if (read_http_payload(ps, buf, sizeof(buf), tmo, &bytes_read))
    goto bugout;

  ps->job_id = 0;
  ps->page_id = 0;

  stat=0;

bugout:
  if (pbb->http_handle)
  {
    http_close(pbb->http_handle);
    pbb->http_handle = 0;
  }
  return stat;   
}; /* cancel_job */

/* --------------------------- LEDM API Calls -----------------------------*/

int bb_open(struct ledm_session *ps)
{
  struct bb_ledm_session *pbb;
  struct device_settings *ds;
  int stat=1, i, j;

  _DBG("bb_open()\n");

  if ((ps->bb_session = create_session()) == NULL)
    goto bugout;

  pbb = ps->bb_session;

  /* Get scanner elements from device. */
  if (get_scanner_elements(ps, &pbb->elements))
  {
    goto bugout;
  }

  /* Determine supported Scan Modes. */
  ds = &pbb->elements.config.settings;
  for(i=0, j=0; i<CE_MAX; i++)
  {
    if (ds->color[i] == CE_K1)
    {
      ps->scanModeList[j] = SANE_VALUE_SCAN_MODE_LINEART;
      ps->scanModeMap[j++] = CE_K1;
    }
    if (ds->color[i] == CE_GRAY8)
    {
       ps->scanModeList[j] = SANE_VALUE_SCAN_MODE_GRAY;
       ps->scanModeMap[j++] = CE_GRAY8;
    }
    if (ds->color[i] == CE_COLOR8)
    {
      ps->scanModeList[j] = SANE_VALUE_SCAN_MODE_COLOR;
      ps->scanModeMap[j++] = CE_COLOR8;
    }
  }
   
  /* Determine scan input sources. */
  i=0;
  if (pbb->elements.config.platen.flatbed_supported)
  {
    ps->inputSourceList[i] = STR_ADF_MODE_FLATBED;
    ps->inputSourceMap[i++] = IS_PLATEN;
  }
  if (pbb->elements.config.adf.supported)
  {
    ps->inputSourceList[i] = STR_ADF_MODE_ADF;
    ps->inputSourceMap[i++] = IS_ADF;
  }
  if (pbb->elements.config.adf.duplex_supported)
  {
    ps->inputSourceList[i] = STR_TITLE_DUPLEX;
    ps->inputSourceMap[i++] = IS_ADF_DUPLEX;
  }

  /* Determine if jpeg quality factor is supported. */
  if (pbb->elements.config.settings.jpeg_quality_factor_supported)
    ps->option[LEDM_OPTION_JPEG_QUALITY].cap &= ~SANE_CAP_INACTIVE;
  else
    ps->option[LEDM_OPTION_JPEG_QUALITY].cap |= SANE_CAP_INACTIVE;


  /* Set flatbed x,y extents. */
  ps->platen_min_width = SANE_FIX(pbb->elements.config.platen.minimum_size.width/1000.0*MM_PER_INCH);
  ps->platen_min_height = SANE_FIX(pbb->elements.config.platen.minimum_size.height/1000.0*MM_PER_INCH);
  ps->platen_tlxRange.max = SANE_FIX(pbb->elements.config.platen.maximum_size.width/11.811023);
  ps->platen_brxRange.max = ps->platen_tlxRange.max;
  ps->platen_tlyRange.max = SANE_FIX(pbb->elements.config.platen.maximum_size.height/11.811023);
  ps->platen_bryRange.max = ps->platen_tlyRange.max;

  /* Set adf/duplex x,y extents. */
  ps->adf_min_width = SANE_FIX(pbb->elements.config.adf.minimum_size.width/1000.0*MM_PER_INCH);
  ps->adf_min_height = SANE_FIX(pbb->elements.config.adf.minimum_size.height/1000.0*MM_PER_INCH);
  ps->adf_tlxRange.max = SANE_FIX(pbb->elements.config.adf.maximum_size.width/11.811023);
  ps->adf_brxRange.max = ps->adf_tlxRange.max;
  ps->adf_tlyRange.max = SANE_FIX(pbb->elements.config.adf.maximum_size.height/11.811023);
  ps->adf_bryRange.max = ps->adf_tlyRange.max;

  i = pbb->elements.config.platen.platen_resolution_list[0] + 1;
  while(i--)
  {
    ps->platen_resolutionList[i] = pbb->elements.config.platen.platen_resolution_list[i];
    ps->resolutionList[i] = pbb->elements.config.platen.platen_resolution_list[i];
  }

  i = pbb->elements.config.adf.adf_resolution_list[0] + 1;
  while(i--) ps->adf_resolutionList[i] = pbb->elements.config.adf.adf_resolution_list[i]; 

  stat = 0;

bugout:
  return stat;
} /* bb_open */

int bb_close(struct ledm_session *ps)
{
  _DBG("bb_close()\n");
  free(ps->bb_session);
  ps->bb_session = NULL;
  return 0;
} 

/* Set scan parameters. If scan has started, use actual known parameters otherwise estimate. */
int bb_get_parameters(struct ledm_session *ps, SANE_Parameters *pp, int option)
{
  struct bb_ledm_session *pbb = ps->bb_session;
  pp->last_frame = SANE_TRUE;
  int factor;

  _DBG("bb_get_parameters(option=%d)\n", option);

  switch(ps->currentScanMode)
  {
    case CE_K1:
      pp->format = SANE_FRAME_GRAY;     /* lineart (GRAY8 converted to MONO by IP) */
      pp->depth = 1;
      factor = 1;
      break;
    case CE_GRAY8:
      pp->format = SANE_FRAME_GRAY;     /* grayscale */
      pp->depth = 8;
      factor = 1;
      break;
    case CE_COLOR8:
    default:
      pp->format = SANE_FRAME_RGB;      /* color */
      pp->depth = 8;
      factor = 3;
      break;
  }

  switch (option)
  {
    case SPO_STARTED:  /* called by xsane */
      if (ps->currentCompression == SF_RAW && ps->currentScanMode != CE_GRAY8)
      {
         /* Set scan parameters based on scan job response values */
        pp->lines = pbb->job.lines;
        pp->pixels_per_line = pbb->job.pixels_per_line;
        pp->bytes_per_line = pbb->job.bytes_per_line;
      }
      else  /* Must be SF_JFIF or ScanMode==CE_BLACK_AND_WHITE1. */
      {
        /* Set scan parameters based on IP. Note for Linart, use IP for hpraw and jpeg. */
        pp->lines = ps->image_traits.lNumRows;
        pp->pixels_per_line = ps->image_traits.iPixelsPerRow;
        pp->bytes_per_line = BYTES_PER_LINE(pp->pixels_per_line, pp->depth * factor);
      }
      break;
    case SPO_STARTED_JR: /* called by sane_start */
      /* Set scan parameters based on scan job response values */
      pp->lines = pbb->job.lines;
      pp->pixels_per_line = pbb->job.pixels_per_line;
      pp->bytes_per_line = pbb->job.bytes_per_line;
      break;
    case SPO_BEST_GUESS:  /* called by xsane & sane_start */
      /* Set scan parameters based on best guess. */
      pp->lines = (int)(SANE_UNFIX(ps->effectiveBry - ps->effectiveTly)/MM_PER_INCH*ps->currentResolution);
      pp->pixels_per_line = floor(SANE_UNFIX(ps->effectiveBrx -ps->effectiveTlx)/MM_PER_INCH*ps->currentResolution);
      pp->bytes_per_line = BYTES_PER_LINE(pp->pixels_per_line, pp->depth * factor);
    default:
      break;
  }
return 0;
}

int bb_is_paper_in_adf(struct ledm_session *ps) /* 0 = no paper in adf, 1 = paper in adf, -1 = error */
{
  char buf[512];
  int bytes_read;
  struct bb_ledm_session *pbb = ps->bb_session;

  if(http_open(ps->dd, HPMUD_S_LEDM_SCAN, &pbb->http_handle) != HTTP_R_OK)
  {
  }
  if (http_write(pbb->http_handle, GET_SCANNER_STATUS, sizeof(GET_SCANNER_STATUS)-1, 120) != HTTP_R_OK)
  {
    //goto bugout;
  }
  read_http_payload(ps, buf, sizeof(buf), EXCEPTION_TIMEOUT, &bytes_read);

  http_close(pbb->http_handle);   /* error, close http connection */
  pbb->http_handle = 0;
  
  if(strstr(buf, "<AdfState>Loaded</AdfState>")) return 1;
  else return 0;
}

char* itoa(int value, char* str, int radix)
{
  static char dig[] = "0123456789""abcdefghijklmnopqrstuvwxyz";
  int n = 0, neg = 0;
  unsigned int v;
  char* p, *q;
  char c;
 
  if (radix == 10 && value < 0)
  {
    value = -value;
    neg = 1;
   }
  v = value;
  do {
    str[n++] = dig[v%radix];
    v /= radix;
  } while (v);
  if (neg)
    str[n++] = '-';
    str[n] = '\0';
 
  for (p = str, q = p + (n-1); p < q; ++p, --q)
    c = *p, *p = *q, *q = c;
  return str;
}

int bb_start_scan(struct ledm_session *ps)
{
  char buf[4096] = {0};

  int len, stat=1, bytes_read;

  ps->bb_session = create_session();
  struct bb_ledm_session *pbb = ps->bb_session;
  char szPage_ID[5] = {0};
  char szJob_ID[5] = {0};

  if (ps->job_id == 0)
  {
	if(http_open(ps->dd, HPMUD_S_LEDM_SCAN, &pbb->http_handle) != HTTP_R_OK)
  	{
    		// goto bugout;
  	}

  	while(1)
  	{
	  if (http_write(pbb->http_handle, GET_SCANNER_STATUS, sizeof(GET_SCANNER_STATUS)-1, 120) != HTTP_R_OK)
	  {
        //goto bugout;
      }
		  
      read_http_payload(ps, buf, sizeof(buf), EXCEPTION_TIMEOUT, &bytes_read);

      if(strstr(buf, "Idle")) break;
  	}
    http_close(pbb->http_handle);   /* error, close http connection */
  	pbb->http_handle = 0;

    if(http_open(ps->dd, HPMUD_S_LEDM_SCAN, &pbb->http_handle) != HTTP_R_OK)
    {
    }

    len = snprintf(buf, sizeof(buf), CREATE_SCAN_JOB_REQUEST,
  		ps->currentResolution,
  		ps->currentResolution,
    	(int) (ps->currentTlx / 5548.7133 ),
    	(int) (ps->currentTly / 5548.7133),
    	(int) (ps->currentBrx / 5548.7133),
    	(int) (ps->currentBry / 5548.7133),
    	"Jpeg",
    	(! strcmp(ce_element[ps->currentScanMode], "Color8")) ? "Color" : (! strcmp(ce_element[ps->currentScanMode], "Gray8")) ? "Gray" : "Gray",
    	((! strcmp(ce_element[ps->currentScanMode], "Color8")) || (! strcmp(ce_element[ps->currentScanMode], "Gray8"))) ? 8: 8,
    	is_element[ps->currentInputSource]);


    /* Write the http post header. Note do not send null termination byte. */
  	if (http_write(pbb->http_handle, POST_HEADER, sizeof(POST_HEADER)-1, 120) != HTTP_R_OK)
 	{
    	//goto bugout;
  	}

  	if (http_write(pbb->http_handle, buf, strlen(buf), 1) != HTTP_R_OK)
  	{
    	//goto bugout;
  	}

  	/* Write zero footer. */
  	if (http_write(pbb->http_handle, ZERO_FOOTER, sizeof(ZERO_FOOTER)-1, 1) != HTTP_R_OK)
  	{
    	//goto bugout;
  	}

  	/* Read response. */
  	if (read_http_payload(ps, buf, sizeof(buf), EXCEPTION_TIMEOUT, &bytes_read))
    	goto bugout;

  	http_close(pbb->http_handle);
  	pbb->http_handle = 0;

  	char joblist[64];
  	char* jl=strstr(buf, "Location:");
  	jl=jl+10;
	
  	int i=0;
  	while(*jl != '\r')
  	{ 
  	joblist[i]=*jl; 
  	jl=jl+1; i++;
  	} 
  	joblist[i]='\0';
	
  	strcpy(ps->url, joblist);
  	char *c=ps->url;
  	c=strstr(c, "JobList");
  	c=c+8;
  	int job_id=strtol(c, NULL, 10);
  	itoa(job_id, szJob_ID,10);
        itoa(1, szPage_ID,10);
        ps->page_id = 1;
  	ps->job_id = job_id;
  }
  else
  {
  	ps->page_id++;
    itoa(ps->job_id,szJob_ID,10);
    itoa(ps->page_id, szPage_ID,10);
  }

  strcpy(buf, "GET /Scan/Jobs/");
  strcat(buf, szJob_ID);
  strcat(buf, "/Pages/");
  strcat(buf, szPage_ID);


  strcat(buf, " HTTP/1.1\r\nHost: localhost\r\nUser-Agent: hplip\r\nAccept: text/plain\r\nAccept-Language: en-us,en\r\nAccept-Charset:utf-8\r\nX-Requested-With: XMLHttpRequest\r\nKeep-Alive: 300\r\nProxy-Connection: keep-alive\r\nCookie: AccessCounter=new\r\n0\r\n\r\n");

  if(http_open(ps->dd, HPMUD_S_LEDM_SCAN, &pbb->http_handle) != HTTP_R_OK)
  {
  }

  if (http_write(pbb->http_handle, buf, strlen(buf), 1) != HTTP_R_OK)
  {
    //goto bugout;
  }

  if (http_read_header(pbb->http_handle, buf, sizeof(buf), 50, &len) != HTTP_R_OK)
    goto bugout;

  if(strstr(buf, "HTTP/1.1 400 Bad Request")) http_read_header(pbb->http_handle, buf, sizeof(buf), 50, &len);
  
  stat=0;
bugout:
  if (stat && pbb->http_handle)
  {
    http_close(pbb->http_handle);   /* error, close http connection */
    pbb->http_handle = 0;
  }
  return stat;
} /* bb_start_scan */

int get_size(struct ledm_session* ps)
{
  struct bb_ledm_session *pbb = ps->bb_session;
  char buffer[7];
  int i=0, tmo=50, len;

  if(ps->currentResolution >= 1200) tmo *= 5;

  while(1)
  {
    if(http_read_size(pbb->http_handle, buffer+i, 1, tmo, &len) == 2) return 0;
    if( i && *(buffer+i) == '\n' && *(buffer+i-1) == '\r') break;
    i++;
  }
  *(buffer+i+1)='\0';
  return strtol(buffer, NULL, 16);
}

int bb_get_image_data(struct ledm_session* ps, int maxLength) 
{
  struct bb_ledm_session *pbb = ps->bb_session;
  int size=0, stat=1;
  char buf_size[2];
  int len=0, tmo=50;

  if(ps->currentResolution >= 1200) tmo *= 5;

  if (ps->cnt == 0)
  {
    size = get_size(ps);
    if(size == 0) 
    { 
      http_read_size(pbb->http_handle, buf_size, 2, tmo, &len);
      http_read_size(pbb->http_handle, buf_size, -1, tmo, &len);
      return 0; 
    }
    http_read_size(pbb->http_handle, ps->buf, size, tmo, &len);
    ps->cnt += len;
    http_read_size(pbb->http_handle, buf_size, 2, tmo, &len);
  }

  return stat=0;
}

int bb_end_page(struct ledm_session *ps, int io_error)
{
   struct bb_ledm_session *pbb = ps->bb_session;

  _DBG("bb_end_page(error=%d)\n", io_error);

   if (pbb->http_handle)
   {
      http_close(pbb->http_handle);
      pbb->http_handle = 0;
   }
   return 0;
}

int bb_end_scan(struct ledm_session* ps, int io_error)
{
  struct bb_ledm_session *pbb = ps->bb_session;

  _DBG("bb_end_scan(error=%d)\n", io_error);

  if (pbb->http_handle)
  {
    http_close(pbb->http_handle);
    pbb->http_handle = 0;
  }
  cancel_job(ps);
  ps->job_id = 0;
  ps->page_id = 0;
  return 0;
}
