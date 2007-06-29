/************************************************************************************\

  soap.h - HP SANE backend support for soap base multi-function peripherals

  (c) 2006 Copyright Hewlett-Packard Development Company, LP

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

#ifndef _SOAP_H
#define _SOAP_H

//#define HAVE_SOAP

#include "hpmud.h"

#ifdef HAVE_SOAP
#include "webScanH.h"
#endif
#include "sane.h"
#include "hpip.h"

#define SOAP_CONTRAST_MIN -127
#define SOAP_CONTRAST_MAX 127
#define SOAP_CONTRAST_DEFAULT 0

#define MM_PER_INCH	25.4

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

enum THREAD_STATE
{
   THREAD_NA = 0,
   THREAD_IDLE,
   THREAD_DATA_AVAIL,
   THREAD_DATA_DONE,
   THREAD_COMPLETE,
   THREAD_ABORTED
};

#define MAX_LIST_SIZE 32
#define MAX_STRING_SIZE 32

#ifdef HAVE_SOAP
typedef struct
{
   char *tag;  /* handle identifier */
   HPMUD_DEVICE dd;  /* hpiod device descriptor */
   HPMUD_CHANNEL sd;  /* hpiod soap channel descriptor */
   char uri[HPLIP_LINE_SIZE];
   char model[HPLIP_LINE_SIZE];
   char ip[128];
   int scantype;

   IP_IMAGE_TRAITS imageTraits;   /* specified by image header */      

   SANE_Option_Descriptor option[SOAP_OPTION_MAX];

   SANE_String_Const scanModeList[MAX_LIST_SIZE];
   enum eColorEntryType scanModeMap[MAX_LIST_SIZE];
   enum eColorEntryType currentScanMode;

   SANE_Int resolutionList[MAX_LIST_SIZE];
   SANE_Int currentResolution;

   SANE_Range contrastRange;
   SANE_Int currentContrast;

   SANE_String_Const compressionList[MAX_LIST_SIZE];
   enum eCompressionType compressionMap[MAX_LIST_SIZE];
   enum eCompressionType currentCompression; 
   enum eDocumentFormat formatMap[MAX_LIST_SIZE];

   SANE_Range jpegQualityRange;
   SANE_Int currentJpegQuality;

   SANE_Range tlxRange, tlyRange, brxRange, bryRange;
   SANE_Fixed currentTlx, currentTly, currentBrx, currentBry;
   SANE_Fixed effectiveTlx, effectiveTly, effectiveBrx, effectiveBry;
   SANE_Fixed minWidth, minHeight;

   pthread_t tid;
   pthread_mutex_t mutex;
   pthread_cond_t data_avail_cond;
   pthread_cond_t data_done_cond;
   unsigned char *sbuf;             /* stream buffer */
   int slen;                        /* stream buffer size in bytes */  
   enum THREAD_STATE dimeState;
   enum THREAD_STATE saneState;

   char scanId[HPLIP_LINE_SIZE];    /* unique scan job identifier */
   IP_HANDLE ipHandle;

   struct soap soap;
} SoapDeviceSession;
#endif

SANE_Status soap_open(SANE_String_Const device, SANE_Handle *handle);
void soap_close(SANE_Handle handle);
const SANE_Option_Descriptor * soap_get_option_descriptor(SANE_Handle handle, SANE_Int option);
SANE_Status soap_control_option(SANE_Handle handle, SANE_Int option, SANE_Action action, void *value, SANE_Int *info);
SANE_Status soap_get_parameters(SANE_Handle handle, SANE_Parameters *params);
SANE_Status soap_start(SANE_Handle handle);
SANE_Status soap_read(SANE_Handle handle, SANE_Byte *data, SANE_Int maxLength, SANE_Int *length);
void soap_cancel(SANE_Handle handle);

#endif  // _SOAP_H


