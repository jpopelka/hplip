/************************************************************************************\

  marvell.c - HP SANE backend support for Marvell based multi-function peripherals

  (c) 2008 Copyright Hewlett-Packard Development Company, LP

  References: 
    ASP Scan Protocol Rev 1.13, Marvell Semiconductor

  Features not support by ASP Scan Protocol:
    1. No jpeg compression between scanner and host. All data is raw.
    2. No lineart (1-bpp monochrome) between scanner and host. Must be performed upstream.
    3. 8x8x8 24-bit RGB is not supported. Only 8x8x8 32-bit XRGB is supported (Windoes uses Planar).
    4. The exact number of lines in the scan job are not known until the end.
    5. XRGB is intermittent. Will use Planar. Planar works ok.
    6. The Planer RGB buffers use ~1.5meg of malloc. Tested ok 256meg Ubuntu 7.10 system. 
       The "top" command showed no more than 8% memory usage during a 1200dpi color scan.

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
#include <sys/types.h>
#include <fcntl.h>
#include <unistd.h>
#include <math.h>
#include "sane.h"
#include "saneopts.h"
#include "hpmud.h"
#include "hpip.h"
#include "common.h"
#include "marvell.h"

#define DEBUG_DECLARE_ONLY
#include "sanei_debug.h"

#define MARVELL_CONTRAST_MIN -127
#define MARVELL_CONTRAST_MAX 127
#define MARVELL_CONTRAST_DEFAULT 0

#define MM_PER_INCH     25.4

enum MARVELL_OPTION_NUMBER
{ 
   MARVELL_OPTION_COUNT = 0,
   MARVELL_OPTION_GROUP_SCAN_MODE,
                   MARVELL_OPTION_SCAN_MODE,
                   MARVELL_OPTION_SCAN_RESOLUTION,
                   MARVELL_OPTION_INPUT_SOURCE,     /* platen, ADF */ 
   MARVELL_OPTION_GROUP_ADVANCED,
                   MARVELL_OPTION_CONTRAST,
   MARVELL_OPTION_GROUP_GEOMETRY,
                   MARVELL_OPTION_TL_X,
                   MARVELL_OPTION_TL_Y,
                   MARVELL_OPTION_BR_X,
                   MARVELL_OPTION_BR_Y,
   MARVELL_OPTION_MAX
};

#define MAX_LIST_SIZE 32
#define MAX_STRING_SIZE 32

#define MARVELL_COOKIE 0x41535001      /* ASP\1 */

enum COLOR_ENTRY
{
   CE_BLACK_AND_WHITE1 = 1,
   CE_GRAY8, 
   CE_RGB24, 
   CE_MAX,
};

enum INPUT_SOURCE 
{
   IS_PLATEN = 1,
   IS_ADF,
   IS_MAX,
};

enum SCAN_STATE
{
   SS_START_JOB = 1,    /* job active */ 
   SS_END_JOB,    /* job in-active */ 
   SS_START_PAGE,    /* page active */ 
   SS_END_PAGE,    /* page in-active */
   SS_START_SHEET,
   SS_END_SHEET,
};

/* Define scan data color information. */
enum MARVELL_SCAN_TYPE
{
   MARVELL_MONO_SCANTYPE,
   MARVELL_COLOR_SCANTYPE,
   MARVELL_THROUGH_COPY_SCANTYPE, // scan to host through copy path (for testing)
};

/* Define scanner lamp control and status state. */
enum MARVELL_LAMP_CTRL_STATUS
{
   MARVELL_LAMP_OFF,
   MARVELL_LAMP_ON,
   MARVELL_GET_LAMP_STATUS,
};

/* Define messages that can be issued between the host and the scanner. */
enum MARVELL_SCAN_MSG
{
    // Resource management
    MARVELL_M_LOCK_SCAN,                     // 0
    MARVELL_M_RELEASE_SCAN,              // 1
    // Scan job control
    MARVELL_M_START_SCAN_JOB,                         // 2
    MARVELL_M_CANCEL_SCAN_JOB,                       // 3
    MARVELL_M_ABORT_SCAN_JOB,                        // 4
    MARVELL_M_SCAN_IMAGE_DATA,                       // 5
    MARVELL_M_GET_SCAN_JOB_SETTINGS,                  // 6
    MARVELL_M_SET_SCAN_JOB_SETTINGS,                  // 7
    MARVELL_M_SET_DEFAULT_SCAN_JOB_SETTINGS,     // 8
    MARVELL_M_START_JOB,                            // 9
    MARVELL_M_START_SHEET,                          // 10
    MARVELL_M_START_PAGE,                           // 11
    MARVELL_M_END_JOB,                              // 12
    MARVELL_M_END_SHEET,                            // 13
    MARVELL_M_END_PAGE,                             // 14
    // ADF Support.
    MARVELL_M_ADF_IS_PAPER_PRESENT,                   // 15
    MARVELL_M_ADF_UNUSED,                          // 16
    MARVELL_M_ADF_EJECT_SHEET,                        // 17
    MARVELL_M_ADF_PICK_NEXT_SHEET,                    // 18
    // For power management.
    MARVELL_M_ENTER_STANDBY,                         // 19
    MARVELL_M_ENTER_READY_STATE,                      // 20
    // For protocol management / recovery
    MARVELL_M_RESET_XMIT_BUFFERS,                     // 21
    MARVELL_M_RESET_TIMEOUT_COUNTER,                 // 22
    MARVELL_M_LAMP_CONTROL,                         // 23
    MARVELL_M_NEW_SCAN_PAGE,                          // 24
};

/* Define command message Status response. */
enum MARVELL_SCAN_RESPONSE
{
    MARVELL_R_OK = 0,
    MARVELL_R_ERROR,
    MARVELL_R_BUSY,
    MARVELL_R_INVALID_CMD,
    MARVELL_R_INVALID_ARG,
    MARVELL_R_ADF_EMPTY,
    MARVELL_R_ADF_MISS_PICK,
    MARVELL_R_ADF_JAM,
};

/* Define scan data format. */
enum MARVELL_SCAN_FORMAT
{
    MARVELL_F_RGB_PACKED = 0,       // Not currently supported
    MARVELL_F_XRGB_PACKED,
    MARVELL_F_PLANAR,          // Used only in SCAN_JOB_SETTINGS
    MARVELL_F_RED,         // Used only in SCAN_DATA_HEADER
    MARVELL_F_GREEN,        // Used only in SCAN_DATA_HEADER
    MARVELL_F_BLUE,         // Used only in SCAN_DATA_HEADER
    MARVELL_F_MONO,
    MARVELL_F_MONO_1BPP,
    MARVELL_F_MONO_2BPP,
    MARVELL_F_MONO_4BPP,
    MARVELL_F_MAX,     // must be last!
};

enum PLANAR_SEL
{
   PS_RED = 0,
   PS_GREEN,
   PS_BLUE,
   PS_MAX
};

/* Define scan job scaling factors. */
struct xy_scale
{
   uint32_t x_numerator;
   uint32_t x_denominator;
   uint32_t y_numerator;
   uint32_t y_denominator;
} __attribute__((packed));

/* 
 * Scan dimensions. Sent from the host to the scanner to set the size and position of the
 * portion of the image to be scanned. Dimensions are specified in hundredths of an inch.
 * Orgin (0,0) is upper left corner.
 */
struct scan_dimensions
{
   uint32_t top;
   uint32_t left;
   uint32_t bottom;
   uint32_t right;
} __attribute__((packed));

/* Define scan job settings that will be in use for the current scan. Can be sent from scanner to host or host to scanner. */
struct scan_job_settings
{
   int32_t gamma;
   int32_t brightness;
   int32_t contrast;
   int32_t resolution;
   struct xy_scale scale;
   int32_t sharp;
   int32_t smooth;
   int32_t bits_per_pixel;
   int32_t reserved1;
   int32_t reserved2;
   int32_t reserved3;
   int32_t reserved4;
   int32_t format;              // From MARVEL_SCAN_FORMAT enum
   struct scan_dimensions scan_window;
   struct scan_dimensions scannable_area; // Read only
   uint32_t type;      // From MARVEL_SCAN_TYPE enum
} __attribute__((packed));

/*
 * Define the packet header. Each packet that is exchanged between the host and the scanner will have a fixed
 * header followed by packet-type dependent data.
 */
struct packet_header
{
   uint32_t cookie;       // version in ASCII
   uint32_t msg;
   int32_t param1;       // message parameters 
   int32_t param2;
   uint32_t status;
   uint32_t size;       // size in bytes of data + sizeof(struct data_header) if scan data
   uint32_t reserved1;
   uint32_t reserved2;
} __attribute__((packed));

/* Scan data header. */
struct data_header
{
   uint32_t format;            // MARVELL_SCAN_FORMAT
   uint32_t row;     // row number
   uint32_t n_rows;  // number of rows in this data_header
   uint32_t bytes_per_pixel;
   uint32_t pixels_per_row; 
   uint32_t pixels_per_row_padded;
} __attribute__((packed));

struct planar_buffer
{
   int cnt;           /* number bytes in buf */
   int index;         /* number bytes read by IP */
   unsigned char buf[489600];    /* room for 16rows * 1200dpi * 8.5inches * 3blocks*/ 
};

struct marvell_session
{
   char *tag;  /* handle identifier */
   HPMUD_DEVICE dd;  /* hpiod device descriptor */
   HPMUD_CHANNEL cd;  /* hpiod soap channel descriptor */
   char uri[HPMUD_LINE_SIZE];
   char model[HPMUD_LINE_SIZE];
   int scantype;

   IP_IMAGE_TRAITS imageTraits;   /* specified by image processor */      
   struct scan_job_settings settings;       /* current scan job settings (valid after sane_open and sane_start) */
   struct data_header job;         /* image attributes specified by scanner. */
   int data_size;
   enum SCAN_STATE job_state;     
   enum SCAN_STATE page_state;     
   enum SCAN_STATE sheet_state;     

   SANE_Option_Descriptor option[MARVELL_OPTION_MAX];

   SANE_String_Const scanModeList[CE_MAX];
   enum COLOR_ENTRY scanModeMap[CE_MAX];
   enum COLOR_ENTRY currentScanMode;

   SANE_String_Const inputSourceList[IS_MAX];
   enum INPUT_SOURCE inputSourceMap[IS_MAX];
   enum INPUT_SOURCE currentInputSource;

   SANE_Int resolutionList[MAX_LIST_SIZE];
   SANE_Int currentResolution;

   SANE_Range contrastRange;
   SANE_Int currentContrast;

   SANE_Range tlxRange, tlyRange, brxRange, bryRange;
   SANE_Fixed currentTlx, currentTly, currentBrx, currentBry;
   SANE_Fixed effectiveTlx, effectiveTly, effectiveBrx, effectiveBry;
   SANE_Fixed minWidth, minHeight;

   IP_HANDLE ipHandle;
   int cnt;
   unsigned char buf[32768];  /* line buffer (max = 1200dpi * 8.5inches * 3) */
   struct planar_buffer pb[PS_MAX];
};

static struct marvell_session *session = NULL;   /* assume one sane_open per process */
static enum PLANAR_SEL format_to_buf[MARVELL_F_MAX] = { 0, 0, 0, PS_RED, PS_GREEN, PS_BLUE };

/* Convert scan_job_settings from network order to host. */
static int convert_settings(struct scan_job_settings *dest, struct scan_job_settings *src)
{
   /* Convert network ordered data to host. */
   dest->gamma = ntohl(src->gamma);
   dest->brightness = ntohl(src->brightness);
   dest->contrast = ntohl(src->contrast);
   dest->resolution = ntohl(src->resolution);
   dest->scale.x_numerator = ntohl(src->scale.x_numerator);
   dest->scale.x_denominator = ntohl(src->scale.x_denominator);
   dest->scale.y_numerator = ntohl(src->scale.y_numerator);
   dest->scale.y_denominator = ntohl(src->scale.y_denominator);
   dest->sharp = ntohl(src->sharp);
   dest->bits_per_pixel = ntohl(src->bits_per_pixel);
   dest->format = ntohl(src->format);
   dest->scan_window.top = ntohl(src->scan_window.top);
   dest->scan_window.left = ntohl(src->scan_window.left);
   dest->scan_window.bottom = ntohl(src->scan_window.bottom);
   dest->scan_window.right = ntohl(src->scan_window.right);
   dest->scannable_area.top = ntohl(src->scannable_area.top);
   dest->scannable_area.left = ntohl(src->scannable_area.left);
   dest->scannable_area.bottom = ntohl(src->scannable_area.bottom);
   dest->scannable_area.right = ntohl(src->scannable_area.right);
   dest->type = ntohl(src->type);

   DBG6("gamma:%d\n", dest->gamma);
   DBG6("brightness:%d\n", dest->brightness);
   DBG6("contrast:%d\n", dest->contrast);
   DBG6("resolution:%d\n", dest->resolution);
   DBG6("x_numerator:%d\n", dest->scale.x_numerator);
   DBG6("x_denominator:%d\n", dest->scale.x_denominator);
   DBG6("y_numerator:%d\n", dest->scale.y_numerator);
   DBG6("y_denominator:%d\n", dest->scale.y_denominator);
   DBG6("sharp:%d\n", dest->sharp);
   DBG6("bits_per_pixel:%d\n", dest->bits_per_pixel);
   DBG6("format:%d\n", dest->format);
   DBG6("scan_win.top:%d\n", dest->scan_window.top);
   DBG6("scan_win.left:%d\n", dest->scan_window.left);
   DBG6("scan_win.bottom:%d\n", dest->scan_window.bottom);
   DBG6("scan_win.right:%d\n", dest->scan_window.right);
   DBG6("scan_area.top:%d\n", dest->scannable_area.top);
   DBG6("scan_area.left:%d\n", dest->scannable_area.left);
   DBG6("scan_area.bottom:%d\n", dest->scannable_area.bottom);
   DBG6("scan_area.right:%d\n", dest->scannable_area.right);
   DBG6("type:%d\n", dest->type);
   return 0;
}

/* Host to scanner command, no scanner reply. */
static int xmit_reset(struct marvell_session *ps)
{
   struct packet_header hd;
   int len;
   int stat=1, tmo=1;

   memset(&hd, 0, sizeof(struct packet_header));
   hd.cookie = htonl(MARVELL_COOKIE);
   hd.msg =  htonl(MARVELL_M_RESET_XMIT_BUFFERS);

   /* Send request message. This message has no response. */
   if (hpmud_write_channel(ps->dd, ps->cd, &hd, sizeof(hd), tmo, &len) != HPMUD_R_OK)
   {
      BUG("invalid xmit_reset %s\n", ps->uri);
      goto bugout;
   }

   sleep(1);   /* wait for scanner to clean-up */
   stat=0;
bugout:
   return stat;
}

/* Wait for scanner to host message. */
static int get_msg(struct marvell_session *ps, struct packet_header *hd, int tmo)
{
   int len;
   int stat=1, total, size;
     
   /* Wait for message header. */
   total = 0;
   size = sizeof(struct packet_header);
   while (total < size)
   {
      if (hpmud_read_channel(ps->dd, ps->cd, (char *)hd+total, size-total, tmo, &len) != HPMUD_R_OK)
      {
         BUG("invalid get_msg %s\n", ps->uri);
         goto bugout;
      }
      total+=len;
   }

   hd->msg = ntohl(hd->msg);
   hd->status = ntohl(hd->status);
   hd->size = ntohl(hd->size);
   hd->param1 = ntohl(hd->param1);
   hd->param2 = ntohl(hd->param2);

   stat=0;

bugout:
   return stat;   
};

/* Wait for a message from the scanner then return. Processes any unsolicted messages. */
static int get_message(struct marvell_session *ps, int tmo, struct packet_header *hd)
{
   struct scan_job_settings sjs;
   int len;
   int stat=1, total, size;
     
   if (get_msg(ps, hd, tmo))
      goto bugout;  

   /* Don't check status on following messages. */
   if (!(hd->msg == MARVELL_M_CANCEL_SCAN_JOB || hd->msg == MARVELL_M_ADF_IS_PAPER_PRESENT))
   {
      if (hd->status != MARVELL_R_OK)
      {
	 BUG("invalid message status: msg=%d status=%d %s\n", hd->msg, hd->status, ps->uri);
	 goto bugout;  
      }
   }

   switch (hd->msg)
   {
      case MARVELL_M_SCAN_IMAGE_DATA:
         DBG6("#scan_image_data\n");
         /* Save image data size. */
         ps->data_size = hd->size - sizeof(struct data_header);
         /* Read scan data header. */
         total = 0;
         size = sizeof(ps->job);
         while (total < size)
         {
            if (hpmud_read_channel(ps->dd, ps->cd, (char *)(&ps->job)+total, size-total, 1, &len) != HPMUD_R_OK)
            {
               BUG("invalid data_header %s\n", ps->uri);
               goto bugout;
            }
            total+=len;
         }
         ps->job.format = ntohl(ps->job.format);
         ps->job.row = ntohl(ps->job.row);
         ps->job.n_rows = ntohl(ps->job.n_rows);
         ps->job.bytes_per_pixel = ntohl(ps->job.bytes_per_pixel);
         ps->job.pixels_per_row = ntohl(ps->job.pixels_per_row);
         ps->job.pixels_per_row_padded = ntohl(ps->job.pixels_per_row_padded);
         DBG6("data_size=%d\n", ps->data_size);
         DBG6("format=%d\n", ps->job.format);
         DBG6("row=%d\n", ps->job.row);
         DBG6("n_rows=%d\n", ps->job.n_rows);
         DBG6("bytes_per_pixel=%d\n", ps->job.bytes_per_pixel);
         DBG6("pixels_per_row=%d\n", ps->job.pixels_per_row);
         DBG6("pixels_per_row_padded=%d\n", ps->job.pixels_per_row_padded);
         break;
      case MARVELL_M_GET_SCAN_JOB_SETTINGS:
         DBG6("#get_scan_job_settings\n");
         total = 0;
         size = sizeof(struct scan_job_settings);    /* assume hd->size == sizeof(struct scan_job_settings) */
         while (total < size)
         {
            if (hpmud_read_channel(ps->dd, ps->cd, (char *)(&sjs)+total, size-total, 1, &len) != HPMUD_R_OK)
            {
               BUG("invalid scan_job_settings %s\n", ps->uri);
               goto bugout;
            }
            total+=len;
         }
         convert_settings(&ps->settings, &sjs);
         break;  
      case MARVELL_M_START_JOB:
         DBG6("#start_job state\n");
         total = 0;
         size = sizeof(struct scan_job_settings);    /* assume hd->size == sizeof(struct scan_job_settings) */
         while (total < size)
         {
            if (hpmud_read_channel(ps->dd, ps->cd, (char *)(&sjs)+total, size-total, 1, &len) != HPMUD_R_OK)
            {
               BUG("invalid scan_job_settings %s\n", ps->uri);
               goto bugout;
            }
            total+=len;
         }
         convert_settings(&ps->settings, &sjs);
         ps->job_state = SS_START_JOB;
         break;  
      case MARVELL_M_START_SHEET:
         DBG6("#start_sheet state\n");
         ps->sheet_state = SS_START_SHEET;
         break;
      case MARVELL_M_START_PAGE:
         DBG6("#start_page state\n");
         ps->page_state = SS_START_PAGE;
         break;
      case MARVELL_M_END_PAGE:
         DBG6("#end_page state\n");
         ps->page_state = SS_END_PAGE;
         break;
      case MARVELL_M_END_JOB:
         DBG6("#end_job state\n");
         ps->job_state = SS_END_JOB;
         break;
      case MARVELL_M_END_SHEET:
         DBG6("#end_sheet state\n");
         ps->sheet_state = SS_END_SHEET;
         break;
      case MARVELL_M_CANCEL_SCAN_JOB:
         DBG6("#cancel_scan_job\n");
         break;
      case MARVELL_M_ABORT_SCAN_JOB:
         DBG6("#abort_scan_job\n");
         break;
      case MARVELL_M_NEW_SCAN_PAGE:
         DBG6("#new_scan_page\n");
         break;
      case MARVELL_M_ADF_IS_PAPER_PRESENT:
         DBG6("#adf_is_paper_present\n");
         break;
      case MARVELL_M_LOCK_SCAN:
         DBG6("#lock_scanner\n");
         break;
      case MARVELL_M_RELEASE_SCAN:
         DBG6("#unlock_scanner\n");
         break;
      case MARVELL_M_START_SCAN_JOB:
         DBG6("#start_scan_job\n");
         break;
      case MARVELL_M_SET_SCAN_JOB_SETTINGS:
         DBG6("#set_scan_job_settings\n");
         break;
      default:
         BUG("invalid get_message msg=%d %s\n", hd->msg, ps->uri);
         goto bugout;
   }

   stat=0;

bugout:
   return stat;      
}

/* Host to scanner command with scanner reply. */
static int cancel_job(struct marvell_session *ps)
{
   struct packet_header hd;
   int len, stat=1, tmo=EXCEPTION_TIMEOUT;

   memset(&hd, 0, sizeof(struct packet_header));
   hd.cookie = htonl(MARVELL_COOKIE);
   hd.msg =  htonl(MARVELL_M_CANCEL_SCAN_JOB);

   /* Send request message. */
   if (hpmud_write_channel(ps->dd, ps->cd, &hd, sizeof(hd), tmo, &len) != HPMUD_R_OK)
   {
      BUG("invalid cancel_job %s\n", ps->uri);
      goto bugout;
   }

   /* Wait for cancel response. Ignor other messages. */
   while (1)
   {
      if (get_message(ps, tmo, &hd))
         goto bugout;
      if (hd.msg == MARVELL_M_CANCEL_SCAN_JOB || hd.msg == MARVELL_M_ABORT_SCAN_JOB)
         break;
   }

   stat = 0;

bugout:
   return stat;   
}

/* Host to scanner command with scanner reply. */
static int is_paper_in_adf(struct marvell_session *ps)
{
   struct packet_header hd;
   int len, stat=-1, tmo=EXCEPTION_TIMEOUT;

   memset(&hd, 0, sizeof(struct packet_header));
   hd.cookie = htonl(MARVELL_COOKIE);
   hd.msg =  htonl(MARVELL_M_ADF_IS_PAPER_PRESENT);

   /* Send request message. */
   if (hpmud_write_channel(ps->dd, ps->cd, &hd, sizeof(hd), tmo, &len) != HPMUD_R_OK)
   {
      BUG("invalid is_paper_in_adf %s\n", ps->uri);
      goto bugout;
   }

   /* Check response. */
   while (1)
   {
      if (get_message(ps, tmo, &hd))
         goto bugout;
      if (hd.msg == MARVELL_M_ADF_IS_PAPER_PRESENT)
         break;
   }
   if (hd.status == MARVELL_R_OK)
      stat = hd.param1; 
   else
      stat = 2;

bugout:
   DBG6("is_paper_in_adf=%d\n", stat);
   return stat;    /* 0 = no paper in adf, 1 = paper in adf, 2 = no adf, -1 = error */
}

/* Host to scanner command with scanner reply. */
static int set_default(struct marvell_session *ps)
{
   struct packet_header hd;
   int len, stat=1, tmo=EXCEPTION_TIMEOUT;

   memset(&hd, 0, sizeof(struct packet_header));
   hd.cookie = htonl(MARVELL_COOKIE);
   hd.msg =  htonl(MARVELL_M_SET_DEFAULT_SCAN_JOB_SETTINGS);

   /* Send request message. */
   if (hpmud_write_channel(ps->dd, ps->cd, &hd, sizeof(hd), tmo, &len) != HPMUD_R_OK)
   {
      BUG("invalid set_default %s\n", ps->uri);
      goto bugout;
   }

   if (get_msg(ps, &hd, tmo))
      goto bugout;

   /* Check response. */
   if (!(hd.msg == MARVELL_M_SET_DEFAULT_SCAN_JOB_SETTINGS))
   {
      BUG("invalid set_default msg=%d, reseting... %s\n", hd.msg, ps->uri);
      xmit_reset(ps);  /* scanner may be in unknown state, try re-syncing */
      goto bugout;  
   }
   if (hd.status != MARVELL_R_OK)
   {
      BUG("invalid set_default status=%d %s\n", hd.status, ps->uri);
      goto bugout;  
   }

   stat = 0;

bugout:
   return stat;   
}

/* Host to scanner command with scanner reply. */
static int lock_scanner(struct marvell_session *ps)
{
   struct packet_header hd;
   int len, stat=1, tmo=EXCEPTION_TIMEOUT;

   memset(&hd, 0, sizeof(struct packet_header));
   hd.cookie = htonl(MARVELL_COOKIE);
   hd.msg =  htonl(MARVELL_M_LOCK_SCAN);

   /* Send request message. */
   if (hpmud_write_channel(ps->dd, ps->cd, &hd, sizeof(hd), tmo, &len) != HPMUD_R_OK)
   {
      BUG("invalid lock_scanner %s\n", ps->uri);
      goto bugout;
   }

   /* Check response. */
   while (1)
   {
      if (get_message(ps, tmo, &hd))
         goto bugout;
      if (hd.msg == MARVELL_M_LOCK_SCAN)
         break;
   }

   stat = 0;

bugout:
   return stat;   
}

/* Host to scanner command with scanner reply. */
static int unlock_scanner(struct marvell_session *ps)
{
   struct packet_header hd;
   int len, stat=1, tmo=EXCEPTION_TIMEOUT;

   memset(&hd, 0, sizeof(struct packet_header));
   hd.cookie = htonl(MARVELL_COOKIE);
   hd.msg =  htonl(MARVELL_M_RELEASE_SCAN);

   /* Send request message. */
   if (hpmud_write_channel(ps->dd, ps->cd, &hd, sizeof(hd), tmo, &len) != HPMUD_R_OK)
   {
      BUG("invalid unlock_scanner %s\n", ps->uri);
      goto bugout;
   }

   /* Check response. */
   while (1)
   {
      if (get_message(ps, tmo, &hd))
         goto bugout;
      if (hd.msg == MARVELL_M_RELEASE_SCAN)
         break;
   }

   stat = 0;

bugout:
   return stat;   
}

/* Host to scanner command with scanner reply. */
static int start_scan_job(struct marvell_session *ps)
{
   struct packet_header hd;
   int len, stat=1, tmo=EXCEPTION_TIMEOUT;

   memset(&hd, 0, sizeof(struct packet_header));
   hd.cookie = htonl(MARVELL_COOKIE);
   hd.msg =  htonl(MARVELL_M_START_SCAN_JOB);

   /* Send request message. */
   if (hpmud_write_channel(ps->dd, ps->cd, &hd, sizeof(hd), tmo, &len) != HPMUD_R_OK)
   {
      BUG("invalid start_scan_job %s\n", ps->uri);
      goto bugout;
   }

   /* Check response. */
   while (1)
   {
      if (get_message(ps, tmo, &hd))
         goto bugout;
      if (hd.msg == MARVELL_M_START_SCAN_JOB)
         break;
   }

   stat = 0;

bugout:
   return stat;   
}

/* Host to scanner command with scanner reply. */
static int set_scan_job_settings(struct marvell_session *ps, struct scan_job_settings *settings)
{
   struct packet_header hd;
   int len, stat=1, tmo=EXCEPTION_TIMEOUT;
   
   memset(&hd, 0, sizeof(struct packet_header));
   hd.cookie = htonl(MARVELL_COOKIE);
   hd.msg = htonl(MARVELL_M_SET_SCAN_JOB_SETTINGS);
   hd.size = htonl(sizeof(struct scan_job_settings));

   /* Write message header. */
   if (hpmud_write_channel(ps->dd, ps->cd, &hd, sizeof(hd), tmo, &len) != HPMUD_R_OK)
   {
      BUG("invalid set_scan_job_settings %s\n", ps->uri);
      goto bugout;
   }
   
   /* Write message data. */
   if (hpmud_write_channel(ps->dd, ps->cd, settings, sizeof(struct scan_job_settings), tmo, &len) != HPMUD_R_OK)
   {
      BUG("invalid set_scan_job_settings %s\n", ps->uri);
      goto bugout;
   }

   /* Verify response. */
   while (1)
   {
      if (get_message(ps, tmo, &hd))
         goto bugout;
      if (hd.msg == MARVELL_M_SET_SCAN_JOB_SETTINGS)
         break;
   }
  
   stat=0;

bugout:
   return stat;   
};

/* Host to scanner command with scanner reply. */
static int get_scan_job_settings(struct marvell_session *ps, struct scan_job_settings *settings)
{
   struct packet_header hd;
   int len, stat=1, tmo=EXCEPTION_TIMEOUT;
   
   memset(&hd, 0, sizeof(struct packet_header));
   hd.cookie = htonl(MARVELL_COOKIE);
   hd.msg = htonl(MARVELL_M_GET_SCAN_JOB_SETTINGS);

   /* Write request message. */
   if (hpmud_write_channel(ps->dd, ps->cd, &hd, sizeof(hd), tmo, &len) != HPMUD_R_OK)
   {
      BUG("invalid get_scan_job_settings %s\n", ps->uri);
      goto bugout;
   }
   
   /* Verify response. */
   while (1)
   {
      if (get_message(ps, tmo, &hd))
         goto bugout;
      if (hd.msg == MARVELL_M_GET_SCAN_JOB_SETTINGS)
         break;
   }

   stat=0;

bugout:
   return stat;   
};

static SANE_Status scan_start(struct marvell_session *ps)
{
   struct packet_header hd;
   struct scan_job_settings sjs;
   int stat, len, tmo=EXCEPTION_TIMEOUT;

   /* If in the middle of ADF scan job send MARVELL_M_NEW_SCAN_PAGE reply. */ 
   if (ps->currentInputSource == IS_ADF && ps->job_state == SS_START_JOB)
   {
      /* This assumes the MARVELL_M_NEW_SCAN_PAGE from scanner was already received. */
      memset(&hd, 0, sizeof(struct packet_header));
      hd.cookie = htonl(MARVELL_COOKIE);
      hd.msg =  htonl(MARVELL_M_NEW_SCAN_PAGE);
      if (hpmud_write_channel(ps->dd, ps->cd, &hd, sizeof(hd), tmo, &len) != HPMUD_R_OK)
      {
	 BUG("invalid new_scan_page_reply %s\n", ps->uri);
         stat = SANE_STATUS_IO_ERROR;
	 goto bugout;
      }
   }
   else
   {
      /* Must be Platen/Flatbed scan or first page of ADF scan. */

      if (lock_scanner(ps))
      {
         stat = SANE_STATUS_DEVICE_BUSY;
         goto bugout;
      }

      /* Write scan job settings. */
      memset(&sjs, 0, sizeof(sjs));
      sjs.gamma = htonl(0x16);
      sjs.brightness = htonl(0x6);
      sjs.contrast = htonl(0x6);
//      sjs.contrast = htonl(ps->currentContrast);
      sjs.resolution = htonl(ps->currentResolution);
      sjs.scale.x_numerator = htonl(0x1);
      sjs.scale.x_denominator = htonl(0x1);
      sjs.scale.y_numerator = htonl(0x1);
      sjs.scale.y_denominator = htonl(0x1);
      sjs.sharp = 0x0;
      sjs.smooth = 0x0;
      sjs.bits_per_pixel = htonl(0x8);
//      sjs.format = htonl(ps->currentScanMode == CE_RGB24 ? MARVELL_F_XRGB_PACKED : MARVELL_F_MONO);
      sjs.format = htonl(ps->currentScanMode == CE_RGB24 ? MARVELL_F_PLANAR : MARVELL_F_MONO);
      sjs.scan_window.top = htonl((int)(SANE_UNFIX(ps->effectiveTly)/MM_PER_INCH*100.0));
      sjs.scan_window.left = htonl((int)(SANE_UNFIX(ps->effectiveTlx)/MM_PER_INCH*100.0));
      sjs.scan_window.bottom = htonl((int)(SANE_UNFIX(ps->effectiveBry)/MM_PER_INCH*100.0));
      sjs.scan_window.right = htonl((int)(SANE_UNFIX(ps->effectiveBrx)/MM_PER_INCH*100.0));
      sjs.scannable_area.top = htonl(ps->settings.scannable_area.top);
      sjs.scannable_area.left = htonl(ps->settings.scannable_area.left);
      sjs.scannable_area.bottom = htonl(ps->settings.scannable_area.bottom);
      sjs.scannable_area.right = htonl(ps->settings.scannable_area.right);
      sjs.type = htonl(ps->currentScanMode == CE_RGB24 ? MARVELL_COLOR_SCANTYPE : MARVELL_MONO_SCANTYPE);
      if (set_scan_job_settings(ps, &sjs))
      {
         stat = SANE_STATUS_IO_ERROR;
         goto bugout;
      }

      /* Tell scanner to start scan job. */
      if (start_scan_job(ps))
      {
         stat = SANE_STATUS_IO_ERROR;
         goto bugout;
      }
   }  /* if (ps->currentInputSource == IS_ADF && ps->job.jobid) */

   stat=SANE_STATUS_GOOD;

bugout:
   return stat;
}

static int assemble_rgb(struct marvell_session *ps)
{
   int i=0, bytes_per_row, index;

   ps->cnt=0;
   if (ps->pb[PS_RED].cnt && ps->pb[PS_GREEN].cnt && ps->pb[PS_BLUE].cnt)
   {
      /* Return one line of RGB. */
      bytes_per_row = ps->job.pixels_per_row_padded * ps->job.bytes_per_pixel;
      index = ps->pb[PS_RED].index;
      for (i=0; i < ps->job.pixels_per_row; i++)
      {
         ps->buf[ps->cnt++] = ps->pb[PS_RED].buf[index+i];
         ps->buf[ps->cnt++] = ps->pb[PS_GREEN].buf[index+i];
         ps->buf[ps->cnt++] = ps->pb[PS_BLUE].buf[index+i];
      }
      ps->pb[PS_RED].cnt -= bytes_per_row;
      ps->pb[PS_GREEN].cnt -= bytes_per_row;
      ps->pb[PS_BLUE].cnt -= bytes_per_row;
      ps->pb[PS_RED].index += bytes_per_row;
      ps->pb[PS_GREEN].index += bytes_per_row;
      ps->pb[PS_BLUE].index += bytes_per_row;
   }
   DBG6("assembled rgb pixels=%d bytes=%d\n", i, ps->cnt); 
   return ps->cnt;
}

static int assemble_gray(struct marvell_session *ps)
{
   int i=0, bytes_per_row, index;

   ps->cnt=0;
   if (ps->pb[PS_RED].cnt)
   {
      /* Return one line of gray. */
      bytes_per_row = ps->job.pixels_per_row_padded * ps->job.bytes_per_pixel;
      index = ps->pb[PS_RED].index;
      for (i=0; i < ps->job.pixels_per_row; i++)
      {
         ps->buf[ps->cnt++] = ps->pb[PS_RED].buf[index+i];
      }
      ps->pb[PS_RED].cnt -= bytes_per_row;
      ps->pb[PS_RED].index += bytes_per_row;
   }
   DBG6("assembled gray pixels=%d bytes=%d\n", i, ps->cnt); 
   return ps->cnt;
}

static int get_image_data(struct marvell_session *ps, int max_length)
{
   struct packet_header hd;
   struct planar_buffer *p;
   int stat=1;
   int len, size, total, tmo=EXCEPTION_TIMEOUT*2;

   if (ps->currentScanMode == CE_RGB24)
   {
      /* If planner data available return it. */
      if (assemble_rgb(ps))
         return 0;

      /* Get next MARVELL_M_SCAN_IMAGE_DATA. If any. */
      if (ps->data_size == 0 && ps->page_state != SS_END_PAGE)
      {
         if (get_message(ps, tmo, &hd))
            goto bugout;
      }

      if (ps->page_state != SS_END_PAGE)
      {
         /* Read three complete color planes. */
         while (1)
         {
            if (ps->pb[PS_RED].cnt)
               if (ps->pb[PS_RED].cnt == ps->pb[PS_GREEN].cnt && ps->pb[PS_RED].cnt == ps->pb[PS_BLUE].cnt)
                  break;   /* done */

            while (ps->data_size > 0)
            {
               p = &ps->pb[format_to_buf[ps->job.format]];
               total = 0;
               size = ps->data_size;
               if ((size + p->cnt) > sizeof(p->buf))
               {
                  BUG("unable to read rgb image data size=%d %s\n", size + p->cnt, ps->uri);
                  goto bugout;
               }
               while (total < size)
               {
                  if (hpmud_read_channel(ps->dd, ps->cd, p->buf+p->cnt+total, size-total, tmo, &len) != HPMUD_R_OK)
                  {
                     BUG("unable to read rgb image data %s\n", ps->uri);
                     goto bugout;
                  }
                  total+=len;
               }
               ps->data_size-=total;
               p->cnt+=total;
               p->index=0;
            }
            if (get_message(ps, tmo, &hd))
               goto bugout;
         }
         DBG6("planar complete redcnt=%d greencnt=%d bluecnt%d\n", ps->pb[PS_RED].cnt, ps->pb[PS_GREEN].cnt, ps->pb[PS_BLUE].cnt);
         assemble_rgb(ps);
      }  /* if (ps->page_state != SS_END_PAGE) */
   }
   else
   {  /* Must be CE_GRAY8. */

      /* If data available return it. */
      if (assemble_gray(ps))
         return 0;

      /* Get next MARVELL_M_SCAN_IMAGE_DATA. If any. */
      if (ps->data_size == 0 && ps->page_state != SS_END_PAGE)
      {
         if (get_message(ps, tmo, &hd))
            goto bugout;
      }

      if (ps->page_state != SS_END_PAGE)
      {
         /* Read all mono data. */
         while (ps->data_size > 0)
         {
            p = &ps->pb[PS_RED];     /* arbitrarily use PS_RED buffer */
            total = 0;
            size = ps->data_size;
	    if ((size + p->cnt) > sizeof(p->buf))
	    {
	       BUG("unable to read gray image data size=%d %s\n", size + p->cnt, ps->uri);
	       goto bugout;
	    }
            while (total < size)
            {
               if (hpmud_read_channel(ps->dd, ps->cd, p->buf+p->cnt+total, size-total, tmo, &len) != HPMUD_R_OK)
               {
                  BUG("unable to read gray image data %s\n", ps->uri);
                  goto bugout;
               }
               total+=len;
            }
            ps->data_size-=total;
            p->cnt+=total;
            p->index=0;
         }
         DBG6("gray complete cnt=%d\n", ps->pb[PS_RED].cnt);
         assemble_gray(ps);
      }  /* if (ps->page_state != SS_END_PAGE) */
   }  /*  if (ps->currentScanMode == CE_RGB24) */

   stat = 0;

bugout:
   return stat;
}

/* Get raw data (ie: uncompressed data) from image processor. */
static int get_ip_data(struct marvell_session *ps, SANE_Byte *data, SANE_Int maxLength, SANE_Int *length)
{
   int ip_ret=IP_INPUT_ERROR;
   unsigned int outputAvail=maxLength, outputUsed=0, outputThisPos;
   unsigned char *input, *output = data;
   unsigned int inputAvail, inputUsed=0, inputNextPos;

   if (!ps->ipHandle)
   {
      BUG("invalid ipconvert state\n");
      goto bugout;
   }
   
   if (get_image_data(ps, outputAvail)) 
      goto bugout;

   if (ps->cnt > 0)
   {
      inputAvail = ps->cnt;
      input = ps->buf;
   }
   else
   {
      input = NULL;   /* no more MARVELL_M_SCAN_IMAGE_DATA, flush ipconvert pipeline */
      inputAvail = 0;
   }

   /* Transform input data to output. Note, output buffer may consume more bytes than input buffer (ie: jpeg to raster). */
   ip_ret = ipConvert(ps->ipHandle, inputAvail, input, &inputUsed, &inputNextPos, outputAvail, output, &outputUsed, &outputThisPos);

   DBG6("input=%p inputAvail=%d inputUsed=%d inputNextPos=%d output=%p outputAvail=%d outputUsed=%d outputThisPos=%d ret=%x\n", input, 
         inputAvail, inputUsed, inputNextPos, output, outputAvail, outputUsed, outputThisPos, ip_ret);

   if (data)
      *length = outputUsed;

   /* For sane do not send output data simultaneously with IP_DONE. */
   if (ip_ret & IP_DONE && outputUsed)
      ip_ret &= ~IP_DONE;                               

bugout:
   return ip_ret;
}

/* Set scan parameters. If scan has started, use actual known parameters otherwise estimate. */  
static int scan_parameters(struct marvell_session *ps, SANE_Parameters *pp, int scan_started)
{
   pp->last_frame = SANE_TRUE;

   /* Set scan parameters based on best guess. */
//   pp->lines = (int)(SANE_UNFIX(ps->effectiveBry - ps->effectiveTly)/MM_PER_INCH*ps->currentResolution);
   pp->lines = -1;      /* unknown */
   pp->pixels_per_line = floor(SANE_UNFIX(ps->effectiveBrx - ps->effectiveTlx)/MM_PER_INCH*ps->currentResolution);

   switch(ps->currentScanMode)
   {
      case CE_BLACK_AND_WHITE1:
         pp->format = SANE_FRAME_GRAY;     /* lineart */
         pp->depth = 1;
         if (scan_started)
         {  /* Use known scan parameters from scan data. */
//            pp->lines = ps->imageTraits.lNumRows;
            pp->pixels_per_line = ps->job.pixels_per_row;
         }
         pp->bytes_per_line = BYTES_PER_LINE(pp->pixels_per_line, pp->depth * 1);
         break;
      case CE_GRAY8:
         pp->format = SANE_FRAME_GRAY;     /* grayscale */
         pp->depth = 8;
         if (scan_started)
         {  /* Use known scan parameters from scan data. */
//            pp->lines = ps->job.n_rows;
            pp->pixels_per_line = ps->job.pixels_per_row;
         }
         pp->bytes_per_line = BYTES_PER_LINE(pp->pixels_per_line, pp->depth * 1);
         break;
      case CE_RGB24:
      default:
         pp->format = SANE_FRAME_RGB;      /* color */
         pp->depth = 8;
         if (scan_started)
         {  /* Use known scan parameters from scan data. */
//            pp->lines = ps->job.n_rows;
            pp->pixels_per_line = ps->job.pixels_per_row;
         }
         pp->bytes_per_line = BYTES_PER_LINE(pp->pixels_per_line, pp->depth * 3);
         break;
   }
   return 0;
}

static struct marvell_session *create_session()
{
   struct marvell_session *ps;

   if ((ps = malloc(sizeof(struct marvell_session))) == NULL)
   {
      BUG("malloc failed: %m\n");
      return NULL;
   }
   memset(ps, 0, sizeof(struct marvell_session));
   ps->tag = "MARVELL";
   ps->dd = -1;
   ps->cd = -1;

   return ps;
}

static int init_options(struct marvell_session *ps)
{
   ps->option[MARVELL_OPTION_COUNT].name = "option-cnt";
   ps->option[MARVELL_OPTION_COUNT].title = SANE_TITLE_NUM_OPTIONS;
   ps->option[MARVELL_OPTION_COUNT].desc = SANE_DESC_NUM_OPTIONS;
   ps->option[MARVELL_OPTION_COUNT].type = SANE_TYPE_INT;
   ps->option[MARVELL_OPTION_COUNT].unit = SANE_UNIT_NONE;
   ps->option[MARVELL_OPTION_COUNT].size = sizeof(SANE_Int);
   ps->option[MARVELL_OPTION_COUNT].cap = SANE_CAP_SOFT_DETECT;
   ps->option[MARVELL_OPTION_COUNT].constraint_type = SANE_CONSTRAINT_NONE;

   ps->option[MARVELL_OPTION_GROUP_SCAN_MODE].name = "mode-group";
   ps->option[MARVELL_OPTION_GROUP_SCAN_MODE].title = SANE_TITLE_SCAN_MODE;
   ps->option[MARVELL_OPTION_GROUP_SCAN_MODE].type = SANE_TYPE_GROUP;

   ps->option[MARVELL_OPTION_SCAN_MODE].name = SANE_NAME_SCAN_MODE;
   ps->option[MARVELL_OPTION_SCAN_MODE].title = SANE_TITLE_SCAN_MODE;
   ps->option[MARVELL_OPTION_SCAN_MODE].desc = SANE_DESC_SCAN_MODE;
   ps->option[MARVELL_OPTION_SCAN_MODE].type = SANE_TYPE_STRING;
   ps->option[MARVELL_OPTION_SCAN_MODE].unit = SANE_UNIT_NONE;
   ps->option[MARVELL_OPTION_SCAN_MODE].size = MAX_STRING_SIZE;
   ps->option[MARVELL_OPTION_SCAN_MODE].cap = SANE_CAP_SOFT_SELECT | SANE_CAP_SOFT_DETECT;
   ps->option[MARVELL_OPTION_SCAN_MODE].constraint_type = SANE_CONSTRAINT_STRING_LIST;
   ps->option[MARVELL_OPTION_SCAN_MODE].constraint.string_list = ps->scanModeList;

   ps->option[MARVELL_OPTION_INPUT_SOURCE].name = SANE_NAME_SCAN_SOURCE;
   ps->option[MARVELL_OPTION_INPUT_SOURCE].title = SANE_TITLE_SCAN_SOURCE;
   ps->option[MARVELL_OPTION_INPUT_SOURCE].desc = SANE_DESC_SCAN_SOURCE;
   ps->option[MARVELL_OPTION_INPUT_SOURCE].type = SANE_TYPE_STRING;
   ps->option[MARVELL_OPTION_INPUT_SOURCE].unit = SANE_UNIT_NONE;
   ps->option[MARVELL_OPTION_INPUT_SOURCE].size = MAX_STRING_SIZE;
   ps->option[MARVELL_OPTION_INPUT_SOURCE].cap = SANE_CAP_SOFT_SELECT | SANE_CAP_SOFT_DETECT;
   ps->option[MARVELL_OPTION_INPUT_SOURCE].constraint_type = SANE_CONSTRAINT_STRING_LIST;
   ps->option[MARVELL_OPTION_INPUT_SOURCE].constraint.string_list = ps->inputSourceList;

   ps->option[MARVELL_OPTION_SCAN_RESOLUTION].name = SANE_NAME_SCAN_RESOLUTION;
   ps->option[MARVELL_OPTION_SCAN_RESOLUTION].title = SANE_TITLE_SCAN_RESOLUTION;
   ps->option[MARVELL_OPTION_SCAN_RESOLUTION].desc = SANE_DESC_SCAN_RESOLUTION;
   ps->option[MARVELL_OPTION_SCAN_RESOLUTION].type = SANE_TYPE_INT;
   ps->option[MARVELL_OPTION_SCAN_RESOLUTION].unit = SANE_UNIT_DPI;
   ps->option[MARVELL_OPTION_SCAN_RESOLUTION].size = sizeof(SANE_Int);
   ps->option[MARVELL_OPTION_SCAN_RESOLUTION].cap = SANE_CAP_SOFT_SELECT | SANE_CAP_SOFT_DETECT;
   ps->option[MARVELL_OPTION_SCAN_RESOLUTION].constraint_type = SANE_CONSTRAINT_WORD_LIST;
   ps->option[MARVELL_OPTION_SCAN_RESOLUTION].constraint.word_list = ps->resolutionList;

   ps->option[MARVELL_OPTION_GROUP_ADVANCED].name = "advanced-group";
   ps->option[MARVELL_OPTION_GROUP_ADVANCED].title = STR_TITLE_ADVANCED;
   ps->option[MARVELL_OPTION_GROUP_ADVANCED].type = SANE_TYPE_GROUP;
   ps->option[MARVELL_OPTION_GROUP_ADVANCED].cap = SANE_CAP_ADVANCED;

   ps->option[MARVELL_OPTION_CONTRAST].name = SANE_NAME_CONTRAST;
   ps->option[MARVELL_OPTION_CONTRAST].title = SANE_TITLE_CONTRAST;
   ps->option[MARVELL_OPTION_CONTRAST].desc = SANE_DESC_CONTRAST;
   ps->option[MARVELL_OPTION_CONTRAST].type = SANE_TYPE_INT;
   ps->option[MARVELL_OPTION_CONTRAST].unit = SANE_UNIT_NONE;
   ps->option[MARVELL_OPTION_CONTRAST].size = sizeof(SANE_Int);
   ps->option[MARVELL_OPTION_CONTRAST].cap = SANE_CAP_SOFT_SELECT | SANE_CAP_SOFT_DETECT | SANE_CAP_ADVANCED;
   ps->option[MARVELL_OPTION_CONTRAST].constraint_type = SANE_CONSTRAINT_RANGE;
   ps->option[MARVELL_OPTION_CONTRAST].constraint.range = &ps->contrastRange;
   ps->contrastRange.min = MARVELL_CONTRAST_MIN;
   ps->contrastRange.max = MARVELL_CONTRAST_MAX;
   ps->contrastRange.quant = 0;

   ps->option[MARVELL_OPTION_GROUP_GEOMETRY].name = "geometry-group";
   ps->option[MARVELL_OPTION_GROUP_GEOMETRY].title = STR_TITLE_GEOMETRY;
   ps->option[MARVELL_OPTION_GROUP_GEOMETRY].type = SANE_TYPE_GROUP;
   ps->option[MARVELL_OPTION_GROUP_GEOMETRY].cap = SANE_CAP_ADVANCED;

   ps->option[MARVELL_OPTION_TL_X].name = SANE_NAME_SCAN_TL_X;
   ps->option[MARVELL_OPTION_TL_X].title = SANE_TITLE_SCAN_TL_X;
   ps->option[MARVELL_OPTION_TL_X].desc = SANE_DESC_SCAN_TL_X;
   ps->option[MARVELL_OPTION_TL_X].type = SANE_TYPE_FIXED;
   ps->option[MARVELL_OPTION_TL_X].unit = SANE_UNIT_MM;
   ps->option[MARVELL_OPTION_TL_X].size = sizeof(SANE_Int);
   ps->option[MARVELL_OPTION_TL_X].cap = SANE_CAP_SOFT_SELECT | SANE_CAP_SOFT_DETECT;
   ps->option[MARVELL_OPTION_TL_X].constraint_type = SANE_CONSTRAINT_RANGE;
   ps->option[MARVELL_OPTION_TL_X].constraint.range = &ps->tlxRange;
   ps->tlxRange.min = 0;
   ps->tlxRange.quant = 0;

   ps->option[MARVELL_OPTION_TL_Y].name = SANE_NAME_SCAN_TL_Y;
   ps->option[MARVELL_OPTION_TL_Y].title = SANE_TITLE_SCAN_TL_Y;
   ps->option[MARVELL_OPTION_TL_Y].desc = SANE_DESC_SCAN_TL_Y;
   ps->option[MARVELL_OPTION_TL_Y].type = SANE_TYPE_FIXED;
   ps->option[MARVELL_OPTION_TL_Y].unit = SANE_UNIT_MM;
   ps->option[MARVELL_OPTION_TL_Y].size = sizeof(SANE_Int);
   ps->option[MARVELL_OPTION_TL_Y].cap = SANE_CAP_SOFT_SELECT | SANE_CAP_SOFT_DETECT;
   ps->option[MARVELL_OPTION_TL_Y].constraint_type = SANE_CONSTRAINT_RANGE;
   ps->option[MARVELL_OPTION_TL_Y].constraint.range = &ps->tlyRange;
   ps->tlyRange.min = 0;
   ps->tlyRange.quant = 0;

   ps->option[MARVELL_OPTION_BR_X].name = SANE_NAME_SCAN_BR_X;
   ps->option[MARVELL_OPTION_BR_X].title = SANE_TITLE_SCAN_BR_X;
   ps->option[MARVELL_OPTION_BR_X].desc = SANE_DESC_SCAN_BR_X;
   ps->option[MARVELL_OPTION_BR_X].type = SANE_TYPE_FIXED;
   ps->option[MARVELL_OPTION_BR_X].unit = SANE_UNIT_MM;
   ps->option[MARVELL_OPTION_BR_X].size = sizeof(SANE_Int);
   ps->option[MARVELL_OPTION_BR_X].cap = SANE_CAP_SOFT_SELECT | SANE_CAP_SOFT_DETECT;
   ps->option[MARVELL_OPTION_BR_X].constraint_type = SANE_CONSTRAINT_RANGE;
   ps->option[MARVELL_OPTION_BR_X].constraint.range = &ps->brxRange;
   ps->brxRange.min = 0;
   ps->brxRange.quant = 0;

   ps->option[MARVELL_OPTION_BR_Y].name = SANE_NAME_SCAN_BR_Y;
   ps->option[MARVELL_OPTION_BR_Y].title = SANE_TITLE_SCAN_BR_Y;
   ps->option[MARVELL_OPTION_BR_Y].desc = SANE_DESC_SCAN_BR_Y;
   ps->option[MARVELL_OPTION_BR_Y].type = SANE_TYPE_FIXED;
   ps->option[MARVELL_OPTION_BR_Y].unit = SANE_UNIT_MM;
   ps->option[MARVELL_OPTION_BR_Y].size = sizeof(SANE_Int);
   ps->option[MARVELL_OPTION_BR_Y].cap = SANE_CAP_SOFT_SELECT | SANE_CAP_SOFT_DETECT;
   ps->option[MARVELL_OPTION_BR_Y].constraint_type = SANE_CONSTRAINT_RANGE;
   ps->option[MARVELL_OPTION_BR_Y].constraint.range = &ps->bryRange;
   ps->bryRange.min = 0;
   ps->bryRange.quant = 0;

   return 0;
}

/* Verify current x/y extents and set effective extents. */ 
static int set_extents(struct marvell_session *ps)
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

/*
 * SANE APIs.
 */

SANE_Status marvell_open(SANE_String_Const device, SANE_Handle *handle)
{
   struct hpmud_model_attributes ma;
   int stat = SANE_STATUS_IO_ERROR;
   int i;

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

   if (hpmud_open_channel(session->dd, HPMUD_S_MARVELL_SCAN_CHANNEL, &session->cd) != HPMUD_R_OK)
   {
      BUG("unable to open %s channel %s\n", HPMUD_S_MARVELL_SCAN_CHANNEL, session->uri);
      stat = SANE_STATUS_DEVICE_BUSY;
      goto bugout;
   }

   /* Get default scanner elements from device. */
   if (set_default(session))
   {
      stat = SANE_STATUS_DEVICE_BUSY;
      goto bugout;
   }
   if (get_scan_job_settings(session, &session->settings))
   {
      stat = SANE_STATUS_IO_ERROR;
      goto bugout;
   }

   /* Init sane option descriptors. */
   init_options(session);  

   /* Set supported Scan Modes and set sane option. */
   i=0;
   session->scanModeList[i] = SANE_VALUE_SCAN_MODE_LINEART;
   session->scanModeMap[i++] = CE_BLACK_AND_WHITE1;
   session->scanModeList[i] = SANE_VALUE_SCAN_MODE_GRAY;
   session->scanModeMap[i++] = CE_GRAY8;
   session->scanModeList[i] = SANE_VALUE_SCAN_MODE_COLOR;
   session->scanModeMap[i++] = CE_RGB24;
   marvell_control_option(session, MARVELL_OPTION_SCAN_MODE, SANE_ACTION_SET_AUTO, NULL, NULL); /* set default option */

   /* Determine scan input source. */
   i=0;
   if (is_paper_in_adf(session) == 2)
   {
      session->inputSourceList[i] = STR_ADF_MODE_FLATBED;
      session->inputSourceMap[i++] = IS_PLATEN;
   }
   else
   {
      session->inputSourceList[i] = STR_ADF_MODE_ADF;
      session->inputSourceMap[i++] = IS_ADF;
   }
   marvell_control_option(session, MARVELL_OPTION_INPUT_SOURCE, SANE_ACTION_SET_AUTO, NULL, NULL); /* set default option */  

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
   marvell_control_option(session, MARVELL_OPTION_SCAN_RESOLUTION, SANE_ACTION_SET_AUTO, NULL, NULL); /* set default option */

   /* Set supported contrast. */
   marvell_control_option(session, MARVELL_OPTION_CONTRAST, SANE_ACTION_SET_AUTO, NULL, NULL); /* set default option */

   /* Set x,y extents. */
   session->minWidth = SANE_FIX(10/100.0*MM_PER_INCH);  /* minimum scan size is one-tenth of a inch */
   session->minHeight = SANE_FIX(10/100.0*MM_PER_INCH);
   session->tlxRange.max = SANE_FIX((session->settings.scannable_area.right - session->settings.scannable_area.left)/100.0*MM_PER_INCH);
   session->brxRange.max = session->tlxRange.max;
   session->tlyRange.max = SANE_FIX((session->settings.scannable_area.bottom - session->settings.scannable_area.top)/100.0*MM_PER_INCH);
   session->bryRange.max = session->tlyRange.max;
   marvell_control_option(session, MARVELL_OPTION_TL_X, SANE_ACTION_SET_AUTO, NULL, NULL); /* set default option */
   marvell_control_option(session, MARVELL_OPTION_TL_Y, SANE_ACTION_SET_AUTO, NULL, NULL); /* set default option */
   marvell_control_option(session, MARVELL_OPTION_BR_X, SANE_ACTION_SET_AUTO, NULL, NULL); /* set default option */
   marvell_control_option(session, MARVELL_OPTION_BR_Y, SANE_ACTION_SET_AUTO, NULL, NULL); /* set default option */

   *handle = (SANE_Handle *)session;

   stat = SANE_STATUS_GOOD;

bugout:

   if (stat != SANE_STATUS_GOOD)
   {
      if (session)
      {
         if (session->cd > 0)
            hpmud_close_channel(session->dd, session->cd);
         if (session->dd > 0)
            hpmud_close_device(session->dd);
         free(session);
         session = NULL;
      }
   }

   return stat;
}

void marvell_close(SANE_Handle handle)
{
   struct marvell_session *ps = (struct marvell_session *)handle;

   DBG8("sane_hpaio_close()\n"); 

   if (ps == NULL || ps != session)
   {
      BUG("invalid sane_close\n");
      return;
   }

   if (ps->dd > 0)
   {
      if (ps->cd > 0)
         hpmud_close_channel(ps->dd, ps->cd);
      hpmud_close_device(ps->dd);
   }
    
   free(ps);
   session = NULL;
}

const SANE_Option_Descriptor *marvell_get_option_descriptor(SANE_Handle handle, SANE_Int option)
{
   struct marvell_session *ps = (struct marvell_session *)handle;

   DBG8("sane_hpaio_get_option_descriptor(option=%s)\n", ps->option[option].name);

   if (option < 0 || option >= MARVELL_OPTION_MAX)
      return NULL;

   return &ps->option[option];
}

SANE_Status marvell_control_option(SANE_Handle handle, SANE_Int option, SANE_Action action, void *value, SANE_Int *set_result)
{
   struct marvell_session *ps = (struct marvell_session *)handle;
   SANE_Int *int_value = value, mset_result=0;
   int i, stat=SANE_STATUS_INVAL;
   char sz[64];

   switch(option)
   {
      case MARVELL_OPTION_COUNT:
         if (action == SANE_ACTION_GET_VALUE)
         {
            *int_value = MARVELL_OPTION_MAX;
            stat = SANE_STATUS_GOOD;
         }
         break;
      case MARVELL_OPTION_SCAN_MODE:
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
                  mset_result |= SANE_INFO_RELOAD_PARAMS | SANE_INFO_RELOAD_OPTIONS;
                  stat = SANE_STATUS_GOOD;
                  break;
               }
            }
         }
         else
         {  /* Set default. */
            ps->currentScanMode = CE_RGB24;
            stat = SANE_STATUS_GOOD;
         }
         break;
      case MARVELL_OPTION_INPUT_SOURCE:
         if (action == SANE_ACTION_GET_VALUE)
         {
            for (i=0; ps->inputSourceList[i]; i++)
            {
               if (ps->currentInputSource == ps->inputSourceMap[i])
               {
                  strcpy(value, ps->inputSourceList[i]);
                  stat = SANE_STATUS_GOOD;
                  break;
               }
            }
         }
         else if (action == SANE_ACTION_SET_VALUE)
         {
            for (i=0; ps->inputSourceList[i]; i++)
            {
               if (strcmp(ps->inputSourceList[i], value) == 0)
               {
                  ps->currentInputSource = ps->inputSourceMap[i];
                  stat = SANE_STATUS_GOOD;
                  break;
               }
            }
         }
         else
         {  /* Set default. */
            ps->currentInputSource = ps->inputSourceMap[0];
            stat = SANE_STATUS_GOOD;
         }
         break;
      case MARVELL_OPTION_SCAN_RESOLUTION:
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
      case MARVELL_OPTION_CONTRAST:
         if (action == SANE_ACTION_GET_VALUE)
         {
            *int_value = ps->currentContrast;
            stat = SANE_STATUS_GOOD;
         }
         else if (action == SANE_ACTION_SET_VALUE)
         {
            if (*int_value >= MARVELL_CONTRAST_MIN && *int_value <= MARVELL_CONTRAST_MAX)
            {
               ps->currentContrast = *int_value;
               stat = SANE_STATUS_GOOD;
               break;
            }
         }
         else
         {  /* Set default. */
            ps->currentContrast = MARVELL_CONTRAST_DEFAULT;
            stat = SANE_STATUS_GOOD;
         }
         break;
      case MARVELL_OPTION_TL_X:
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
      case MARVELL_OPTION_TL_Y:
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
      case MARVELL_OPTION_BR_X:
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
      case MARVELL_OPTION_BR_Y:
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
            BUG("value=%d brymin=%d brymax=%d\n", *int_value, ps->bryRange.min, ps->bryRange.max);
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

SANE_Status marvell_get_parameters(SANE_Handle handle, SANE_Parameters *params)
{
   struct marvell_session *ps = (struct marvell_session *)handle;

   set_extents(ps);

   scan_parameters(ps, params, ps->ipHandle ? 1 : 0);

   DBG8("sane_hpaio_get_parameters(): format=%d, last_frame=%d, lines=%d, depth=%d, pixels_per_line=%d, bytes_per_line=%d\n",
                    params->format, params->last_frame, params->lines, params->depth, params->pixels_per_line, params->bytes_per_line);

   return SANE_STATUS_GOOD;
}

SANE_Status marvell_start(SANE_Handle handle)
{
   struct packet_header hd;
   struct marvell_session *ps = (struct marvell_session *)handle;
   SANE_Parameters pp;
   IP_IMAGE_TRAITS traits;
   IP_XFORM_SPEC xforms[IP_MAX_XFORMS], *pXform=xforms;
   int stat, ret, tmo=EXCEPTION_TIMEOUT*2;

   DBG8("sane_hpaio_start()\n");

   if (set_extents(ps))
   {
      BUG("invalid extents: tlx=%d brx=%d tly=%d bry=%d minwidth=%d minheight%d maxwidth=%d maxheight=%d\n",
         ps->currentTlx, ps->currentTly, ps->currentBrx, ps->currentBry, ps->minWidth, ps->minHeight, ps->tlxRange.max, ps->tlyRange.max);
      stat = SANE_STATUS_INVAL;
      goto bugout;
   }   

   /* Get current scanner state. */
   if (get_scan_job_settings(ps, &ps->settings))
   {
      stat = SANE_STATUS_IO_ERROR;
      goto bugout;
   }

   /* If input is ADF and ADF is empty, return SANE_STATUS_NO_DOCS. */
   if (ps->currentInputSource == IS_ADF)
   {
      ret = is_paper_in_adf(ps);
      if (ret == 0)
      {
         stat = SANE_STATUS_NO_DOCS;
         goto bugout;
      }
      else if (ret < 0)
      {
         stat = SANE_STATUS_IO_ERROR;
         goto bugout;
      }
   }

   /* Start scan and get actual image traits. */
   if ((ret = scan_start(ps)) != SANE_STATUS_GOOD)
   {
      BUG("unable to start scan\n");
      stat = ret;
      goto bugout;
   }

   memset(xforms, 0, sizeof(xforms));    

   /* Setup image-processing pipeline for xform. */
   if (ps->currentScanMode == CE_BLACK_AND_WHITE1)
   {
      pXform->aXformInfo[IP_GRAY_2_BI_THRESHOLD].dword = 127;
      ADD_XFORM(X_GRAY_2_BI);
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

   /* Get actual input image attributes from "struct data_header". */
   while (!ps->data_size)
   {
      if (get_message(ps, tmo, &hd))
      {
         BUG("unable get scan data_header\n");
         stat = SANE_STATUS_IO_ERROR;
         goto bugout;
      }
   }
   scan_parameters(ps, &pp, 1);

   /* Now set known input image attributes. */
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
   traits.lNumRows = pp.lines;
   traits.iNumPages = 1;
   traits.iPageNum = 1;
   traits.iComponentsPerPixel = ((traits.iBitsPerPixel % 3) ? 1 : 3);
   ipSetDefaultInputTraits(ps->ipHandle, &traits);

   /* Get output image attributes from the image processor. */
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
      if (stat == SANE_STATUS_IO_ERROR)
         ps->job_state = ps->page_state = ps->sheet_state = ps->data_size = 0;
   }

   return stat;
}

SANE_Status marvell_read(SANE_Handle handle, SANE_Byte *data, SANE_Int maxLength, SANE_Int *length)
{
   struct packet_header hd;
   struct marvell_session *ps = (struct marvell_session *)handle;
   int ret, stat=SANE_STATUS_IO_ERROR, tmo=EXCEPTION_TIMEOUT;

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

      if (stat != SANE_STATUS_IO_ERROR)
      {
         /* If SS_START_SHEET was used, get SS_END_SHEET. */
         if (ps->sheet_state == SS_START_SHEET)
            get_message(ps, tmo, &hd);

         if (ps->currentInputSource == IS_PLATEN)
         {
            /* Done with scanner so close it down. */
            if (ps->job_state == SS_START_JOB)
               get_message(ps, tmo, &hd);
            unlock_scanner(ps);
         }
      }
      ps->page_state = ps->sheet_state = ps->data_size = 0;
   }

   DBG8("-sane_hpaio_read() output=%p bytes_read=%d maxLength=%d status=%d\n", data, *length, maxLength, stat);

   return stat;
}

void marvell_cancel(SANE_Handle handle)
{
   struct marvell_session *ps = (struct marvell_session *)handle;

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
   if (ps->job_state == SS_START_JOB)
      cancel_job(ps);
   if (ps->currentInputSource == IS_ADF && ps->job_state)
      unlock_scanner(ps);
   ps->job_state = ps->page_state = ps->sheet_state = ps->data_size = 0;
}

