/*****************************************************************************\

  hp.c - hp cups backend 
 
  (c) 2004 Copyright Hewlett-Packard Development Company, LP

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

\*****************************************************************************/

#include <sys/types.h>
#include <sys/stat.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h>
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <string.h>
#include <unistd.h>
#include <stdarg.h>
#include <syslog.h>
#include "hpmud.h"

#define RETRY_TIMEOUT 30  /* seconds */
#define EXCEPTION_TIMEOUT 45 /* seconds */

#define NFAULT_BIT  0x08
#define PERROR_BIT  0x20

#define OOP             (NFAULT_BIT | PERROR_BIT)
#define JAMMED          (PERROR_BIT)
#define ERROR_TRAP      (0)

#define STATUS_MASK (NFAULT_BIT | PERROR_BIT)

#define DEVICE_IS_OOP(reg)  ((reg & STATUS_MASK) == OOP)
#define DEVICE_PAPER_JAMMED(reg)  ((reg & STATUS_MASK) == JAMMED)
#define DEVICE_IO_TRAP(reg)       ((reg & STATUS_MASK) == ERROR_TRAP)

#define HEX2INT(x, i) if (x >= '0' && x <= '9')      i |= x - '0'; \
                       else if (x >= 'A' && x <= 'F') i |= 0xA + x - 'A'; \
                       else if (x >= 'a' && x <= 'f') i |= 0xA + x - 'a'

/* Actual vstatus codes are mapped to 1000+vstatus for DeviceError messages. */ 
typedef enum
{
   VSTATUS_IDLE = 1000,
   VSTATUS_BUSY,
   VSTATUS_PRNT,      /* io printing */
   VSTATUS_OFFF,      /* turning off */
   VSTATUS_RPRT,      /* report printing */
   VSTATUS_CNCL,      /* canceling */
   VSTATUS_IOST,      /* io stall */
   VSTATUS_DRYW,      /* dry time wait */
   VSTATUS_PENC,      /* pen change */
   VSTATUS_OOPA,      /* out of paper */
   VSTATUS_BNEJ,      /* banner eject needed */
   VSTATUS_BNMZ,      /* banner mismatch */
   VSTATUS_PHMZ,      /* photo mismatch */
   VSTATUS_DPMZ,      /* duplex mismatch */
   VSTATUS_PAJM,      /* media jam */
   VSTATUS_CARS,      /* carriage stall */
   VSTATUS_PAPS,      /* paper stall */
   VSTATUS_PENF,      /* pen failure */
   VSTATUS_ERRO,      /* hard error */
   VSTATUS_PWDN,      /* power down */
   VSTATUS_FPTS,      /* front panel test */
   VSTATUS_CLNO       /* clean out tray missing */
} VSTATUS;


#define EVENT_START_JOB 500
#define EVENT_END_JOB 501

static int bug(const char *fmt, ...)
{
   char buf[256];
   va_list args;
   int n;

   va_start(args, fmt);

   if ((n = vsnprintf(buf, 256, fmt, args)) == -1)
      buf[255] = 0;     /* output was truncated */

   fprintf(stderr, buf);
   syslog(LOG_WARNING, buf);

   fflush(stderr);
   va_end(args);
   return n;
}

static const char *GetVStatusMessage(VSTATUS status)
{
   char *p;

   /* Map VStatus to text message. TODO: text needs to be localized. */
   switch(status)
   {
      case(VSTATUS_IDLE):
         p = "ready to print";
         break;
      case(VSTATUS_BUSY):
         p = "busy";
         break;
      case(VSTATUS_PRNT):
         p = "i/o printing";
         break;
      case(VSTATUS_OFFF):
         p = "turning off";
         break;
      case(VSTATUS_RPRT):
         p = "report printing";
         break;
      case(VSTATUS_CNCL):
         p = "canceling";
         break;
      case(VSTATUS_IOST):
         p = "incomplete job";
         break;
      case(VSTATUS_DRYW):
         p = "dry time wait";
         break;
      case(VSTATUS_PENC):
         p = "pen change";
         break;
      case(VSTATUS_OOPA):
         p = "out of paper";
         break;
      case(VSTATUS_BNEJ):
         p = "banner eject needed";
         break;
      case(VSTATUS_BNMZ):
         p = "banner mismatch";
         break;
      case(VSTATUS_DPMZ):
         p = "duplex mismatch";
         break;
      case(VSTATUS_PAJM):
         p = "media jam";
         break;
      case(VSTATUS_CARS):
         p = "carriage stall";
         break;
      case(VSTATUS_PAPS):
         p = "paper stall";
         break;
      case(VSTATUS_PENF):
         p = "pen failure";
         break;
      case(VSTATUS_ERRO):
         p = "hard error";
         break;
      case(VSTATUS_PWDN):
         p = "power down";
         break;
      case(VSTATUS_FPTS):
         p = "front panel test";
         break;
      case(VSTATUS_CLNO):
         p = "clean out tray missing";
         break;
      case(5000+HPMUD_R_IO_ERROR):
         p = "check device";
         break;
      default:
         p = "unknown state";
         bug("INFO: printer state=%d\n", status);
         break;
   }
   return p;
}

static int GetVStatus(HPMUD_DEVICE dd)
{
   char id[1024];
   char *pSf;
   int vstatus=VSTATUS_IDLE, ver, len;
   enum HPMUD_RESULT r;

   r = hpmud_get_device_id(dd,  id, sizeof(id), &len);
   if (!(r == HPMUD_R_OK || r == HPMUD_R_DEVICE_BUSY))
   {
      vstatus = 5000+HPMUD_R_IO_ERROR;      /* no deviceid, return some error */
      goto bugout;
   }
   
   /* Check for valid S-field in device id string. */
   if ((pSf = strstr(id, ";S:")) == NULL)
   {
      /* No S-field, use status register instead of device id. */ 
      unsigned int status;
      hpmud_get_device_status(dd, &status);      
      if (DEVICE_IS_OOP(status))
         vstatus = VSTATUS_OOPA;
      else if (DEVICE_PAPER_JAMMED(status))
         vstatus = VSTATUS_PAJM;
      else if (DEVICE_IO_TRAP(status))
         vstatus = VSTATUS_CARS;
      else
         vstatus = 5000+HPMUD_R_IO_ERROR;      /* nothing in status, return some error */
   }
   else
   {
      /* Valid S-field, get version number. */
      pSf+=3;
      ver = 0; 
      HEX2INT(*pSf, ver);
      pSf++;
      ver = ver << 4;
      HEX2INT(*pSf, ver);
      pSf++;

      /* Position pointer to printer state subfield. */
      switch (ver)
      {
         case 0:
         case 1:
         case 2:
            pSf+=12;
            break;
         case 3:
            pSf+=14;
            break;
         case 4:
            pSf+=18;
            break;
         default:
            bug("WARNING: unknown S-field version=%d\n", ver);
            pSf+=12;
            break;            
      }

      /* Extract VStatus.*/
      vstatus = 0; 
      HEX2INT(*pSf, vstatus);
      pSf++;
      vstatus = vstatus << 4;
      HEX2INT(*pSf, vstatus);
      vstatus += 1000;
   }

bugout:
   return vstatus;
}

static int DevDiscovery()
{
   char buf[HPMUD_LINE_SIZE*64];
   int cnt=0, bytes_read, r=1;  
   enum HPMUD_RESULT stat;

   stat = hpmud_probe_devices(HPMUD_BUS_ALL, buf, sizeof(buf), &cnt, &bytes_read);

   if (stat != HPMUD_R_OK)
      goto bugout;

   if (cnt == 0)
#ifdef HAVE_CUPS11
      fprintf(stdout, "direct hp:/no_device_found \"Unknown\" \"hp no_device_found\"\n");
#else
      fprintf(stdout, "direct hp \"Unknown\" \"HP Printer (HPLIP)\"\n");
#endif
   else
      fprintf(stdout, "%s", buf);

   r = 0;

bugout:
   return r;
}

#if 0
static int DeviceEvent(char *dev, char *jobid, int code, char *type, int timeout)
{
   char message[512];  
   int len=0;
 
   if (hplip_session->hpssd_socket < 0)
      goto mordor;  

   if (timeout == 0)
      len = sprintf(message, "msg=Event\ndevice-uri=%s\njob-id=%s\nevent-code=%d\nevent-type=%s\n", dev, jobid, code, type);
   else
      len = sprintf(message, "msg=Event\ndevice-uri=%s\njob-id=%s\nevent-code=%d\nevent-type=%s\nretry-timeout=%d\n", 
                     dev, jobid, code, type, timeout);
 
   /* Send message with no response. */
   if (send(hplip_session->hpssd_socket, message, len, 0) == -1) 
   {  
      bug("unable to send Event %s %s %d: %m\n", dev, jobid, code);
   }  

mordor:

   return 0;
}
#endif

static int DeviceEvent(char *dev, char *jobid, int code, char *type, int timeout)
{
   return 0;
}

int main(int argc, char *argv[])
{
   int fd;
   int copies;
   int len, vstatus, cnt;
   char buf[HPMUD_BUFFER_SIZE];
   struct hpmud_model_attributes ma;
   int paperout=0, offline=0;
   HPMUD_DEVICE hd=-1;
   HPMUD_CHANNEL cd=-1;
   int n, total, retry=0, size;
   enum HPMUD_RESULT stat;

   if (argc > 1)
   {
      const char *arg = argv[1];
      if ((arg[0] == '-') && (arg[1] == 'h'))
      {
         fprintf(stdout, "HP Linux Imaging and Printing System\nCUPS Backend %s\n", VERSION);
         fprintf(stdout, "(c) 2003-2007 Copyright Hewlett-Packard Development Company, LP\n");
         exit(0);
      }
   }

   if (argc == 1)
      exit (DevDiscovery());

   if (argc < 6 || argc > 7)
   {
      bug("ERROR: invalid usage: device_uri job-id user title copies options [file]\n");
      exit (1);
   }

   if (argc == 6)
   {
      fd = 0;         /* use stdin. */
      copies = 1;
   }
   else
   {
      if ((fd = open(argv[6], O_RDONLY)) < 0)  /* use specified file */ 
      {
         bug("ERROR: unable to open print file %s: %m\n", argv[6]);
         exit (1);
      }
      copies = atoi(argv[4]);
   }

   /* Get any parameters needed for DeviceOpen. */
   hpmud_query_model(argv[0], &ma);  

   DeviceEvent(argv[0], argv[1], EVENT_START_JOB, "event", 0);

   /* Open hp device. */
   while ((stat = hpmud_open_device(argv[0], ma.prt_mode, &hd)) != HPMUD_R_OK)
   {
       /* Display user error. */
       DeviceEvent(argv[0], argv[1], 5000+stat, "error", RETRY_TIMEOUT);

       bug("INFO: open device failed; will retry in %d seconds...\n", RETRY_TIMEOUT);
       sleep(RETRY_TIMEOUT);
       retry = 1;
   }

   if (retry)
   {
      /* Clear user error. */
      DeviceEvent(argv[0], argv[1], VSTATUS_PRNT, "event", 0);
      retry=0;
   }

   /* Write print file. */
   while (copies > 0)
   {
      copies--;

      if (fd != 0)
      {
         fputs("PAGE: 1 1\n", stderr);
         lseek(fd, 0, SEEK_SET);
      }

      while ((len = read(fd, buf, sizeof(buf))) > 0)
      {
         size=len;
         total=0;

         while (size > 0)
         {
            /* Got some data now open the print channel. This will handle any HPIJS print channel contention. */
            if (cd <= 0)
            {
               while ((stat = hpmud_open_channel(hd, HPMUD_S_PRINT_CHANNEL, &cd)) != HPMUD_R_OK)
               {
                  DeviceEvent(argv[0], argv[1], 5000+stat, "error", RETRY_TIMEOUT);
                  bug("INFO: open print channel failed; will retry in %d seconds...\n", RETRY_TIMEOUT);
                  sleep(RETRY_TIMEOUT);
                  retry = 1;
               }

               if (retry)
               {
                  /* Clear user error. */
                  DeviceEvent(argv[0], argv[1], VSTATUS_PRNT, "event", 0);
                  retry=0;
               }
            }

            stat = hpmud_write_channel(hd, cd, buf+total, size, EXCEPTION_TIMEOUT, &n);

            if (n != size)
            {
               /* IO error, get printer status. */
               vstatus = GetVStatus(hd);

               /* Display user error. */
               DeviceEvent(argv[0], argv[1], vstatus, "error", RETRY_TIMEOUT);

               switch (vstatus)
               {
                  case VSTATUS_OOPA:
                     if (!paperout)
                     {
                        fputs("STATE: +media-empty-error\n", stderr);
                        paperout=1;
                     }
                     break;
                  default:
                     if (!offline)
                     {
                        fputs("STATE: +other\n", stderr);
                        offline=1;
                     }
                     break;
               }

               bug("ERROR: %s; will retry in %d seconds...\n", GetVStatusMessage(vstatus), RETRY_TIMEOUT);
               sleep(RETRY_TIMEOUT);
               retry = 1;

            }
            else
            {
               if (paperout || offline)
                  bug("INFO: Printing...\n");

               if (paperout)
               {
                  paperout = 0;
                  fputs("STATE: -media-empty-error\n", stderr);
               }
               if (offline)
               {
                  offline = 0;
                  fputs("STATE: -other\n", stderr);
               }
            }
            total+=n;
            size-=n;
         }   /* while (size > 0) */

         if (retry)
         {
            /* Clear user error. */
            DeviceEvent(argv[0], argv[1], VSTATUS_PRNT, "event", 0);
            retry=0;
         }
      }   /* while ((len = read(fd, buf, HPLIP_BUFFER_SIZE)) > 0) */
   }   /* while (copies > 0) */

   /* Wait for I/O to complete over the wire. */
   sleep(2);

   /* If not uni-di mode, monitor printer status and wait for I/O to finish. */
   if (ma.prt_mode != HPMUD_UNI_MODE)
   {
      /*
       * Since hpiod uses non-blocking i/o (bi-di) we must make sure the printer has received all data
       * before closing the print channel. Otherwise data will be lost.
       */
      vstatus = GetVStatus(hd);
      if (vstatus < 5000)
      {
         /* Got valid status, wait for idle. */
         cnt=0;
         while ((vstatus != VSTATUS_IDLE) && (vstatus < 5000) && (cnt < 5))
         {
           sleep(2);
           vstatus = GetVStatus(hd);
           cnt++;
         } 
      }
      else
      {
         /* No valid status, use fixed delay. */
         sleep(8);
      }
   }
   
   DeviceEvent(argv[0], argv[1], EVENT_END_JOB, "event", 0);
   fprintf(stderr, "INFO: %s\n", GetVStatusMessage(VSTATUS_IDLE));

   if (cd >= 0)
      hpmud_close_channel(hd, cd);
   if (hd >= 0)
      hpmud_close_device(hd);   
   if (fd != 0)
      close(fd);

   exit (0);
}

