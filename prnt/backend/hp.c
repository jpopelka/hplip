/*****************************************************************************\

  hp.c - hp cups backend 
 
  (c) 2004-2007 Copyright Hewlett-Packard Development Company, LP

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

#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

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
#include <ctype.h>
#include <pthread.h>
#include "hpmud.h"

//#define HP_DEBUG

struct pjl_attributes
{
   int pjl_device;   /* 0=disabled, 1=enabled */
   int current_status;
   int eoj_pages;        /* end-of-job pages */
   int abort;         /* 0=no, 1=yes */
   int done;          /* 0=no, 1=yes */
   HPMUD_DEVICE dd;
   HPMUD_CHANNEL cd;
   pthread_t tid;
   pthread_mutex_t mutex;
   pthread_cond_t done_cond;
};

#define _STRINGIZE(x) #x
#define STRINGIZE(x) _STRINGIZE(x)

#define BUG(args...) bug(__FILE__ " " STRINGIZE(__LINE__) ": " args)

#ifdef HP_DEBUG
   #define DBG(args...) syslog(LOG_INFO, __FILE__ " " STRINGIZE(__LINE__) ": " args)
   #define DBG_DUMP(data, size) sysdump((data), (size))
   #define DBG_SZ(args...) syslog(LOG_INFO, args)
#else
   #define DBG(args...)
   #define DBG_DUMP(data, size)
   #define DBG_SZ(args...)
#endif

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

//const char pjl_status_cmd[] = "\e%-12345X@PJL INFO STATUS \r\n\e%-12345X";
static const char pjl_ustatus_cmd[] = "\e%-12345X@PJL USTATUS DEVICE = ON \r\n@PJL USTATUS JOB = ON \r\n@PJL JOB \r\n\e%-12345X";
static const char pjl_job_end_cmd[] = "\e%-12345X@PJL EOJ \r\n\e%-12345X";
static const char pjl_ustatus_off_cmd[] = "\e%-12345X@PJL USTATUSOFF \r\n\e%-12345X";

static int bug(const char *fmt, ...)
{
   char buf[256];
   va_list args;
   int n;

   va_start(args, fmt);

   if ((n = vsnprintf(buf, 256, fmt, args)) == -1)
      buf[255] = 0;     /* output was truncated */

   fprintf(stderr, buf);
   syslog(LOG_ERR, buf);

   fflush(stderr);
   va_end(args);
   return n;
}

#ifdef HP_DEBUG
static void sysdump(const void *data, int size)
{
    /* Dump size bytes of *data. Output looks like:
     * [0000] 75 6E 6B 6E 6F 77 6E 20 30 FF 00 00 00 00 39 00 unknown 0.....9.
     */

    unsigned char *p = (unsigned char *)data;
    unsigned char c;
    int n;
    char bytestr[4] = {0};
    char addrstr[10] = {0};
    char hexstr[16*3 + 5] = {0};
    char charstr[16*1 + 5] = {0};
    for(n=1;n<=size;n++) {
        if (n%16 == 1) {
            /* store address for this line */
            snprintf(addrstr, sizeof(addrstr), "%.4d", (int)((p-(unsigned char *)data) & 0xffff));
        }
            
        c = *p;
        if (isprint(c) == 0) {
            c = '.';
        }

        /* store hex str (for left side) */
        snprintf(bytestr, sizeof(bytestr), "%02X ", *p);
        strncat(hexstr, bytestr, sizeof(hexstr)-strlen(hexstr)-1);

        /* store char str (for right side) */
        snprintf(bytestr, sizeof(bytestr), "%c", c);
        strncat(charstr, bytestr, sizeof(charstr)-strlen(charstr)-1);

        if(n%16 == 0) { 
            /* line completed */
            DBG_SZ("[%4.4s]   %-50.50s  %s\n", addrstr, hexstr, charstr);
            hexstr[0] = 0;
            charstr[0] = 0;
        }
        p++; /* next byte */
    }

    if (strlen(hexstr) > 0) {
        /* print rest of buffer if not empty */
        DBG_SZ("[%4.4s]   %-50.50s  %s\n", addrstr, hexstr, charstr);
    }
}
#endif

/* Map printer status to IPP printer-state-reasons (see RFC-2911). */
static int map_ipp_printer_state_reason(int status, const char **state_msg)
{
   
   if (status >= 1000 && status <= 1999)
   {
      /* inkjet vstatus */
      switch (status)
      {
         case VSTATUS_IDLE:
         case VSTATUS_PRNT:
            *state_msg = "none";
            break;
         case VSTATUS_OOPA:
            *state_msg = "media-empty-error";
            break;
         case(VSTATUS_PAJM):
            *state_msg = "media-jam-error";
            break;
         default:
            *state_msg = "other";
            break;
      }
   }
   else if (status >= 10000 && status <= 55999)
   {
      /* laserjet pjl status */
      if (status >= 10000 && status <= 10999)
         *state_msg = "none";
      else if (status >= 41000 && status <= 41999)
         *state_msg = "media-empty-error";
      else if ((status >= 42000 && status <= 42999) || (status >= 44000 && status <= 44999) || (status == 40022))
         *state_msg = "media-jam-error";
      else if (status == 40021)
         *state_msg = "cover-open-error";
      else if (status == 40600)
         *state_msg = "toner-empty-error";
      else
         *state_msg = "other";      
   }
   else
   {
      /* Assume hpmud error */
      *state_msg = "other";
   }

   return 0;
}

static enum HPMUD_RESULT get_pjl_input(HPMUD_DEVICE dd, HPMUD_CHANNEL cd, char *buf, int buf_size, int sec_timeout, int *bytes_read)
{
   enum HPMUD_RESULT stat;
   int len;

   *bytes_read = 0;

   /* Read unsolicited status from device. */   
   stat = hpmud_read_channel(dd, cd, buf, buf_size, sec_timeout, &len);
   if (stat != HPMUD_R_OK)
      goto bugout;

   buf[len]=0;

   DBG("pjl result len=%d\n", len);
   DBG_DUMP(buf, len);

   *bytes_read = len;

   stat = HPMUD_R_OK;

bugout:
   return stat;
}

static int parse_pjl_job_end(char *buf, int *pages)
{
   char *p, *tail;
   int stat=0;

   if (buf[0] == 0)
      goto bugout;

   if ((p = strcasestr(buf, "ustatus job")) != NULL)
   {
      if (strncasecmp(p+13, "end", 3) == 0)
      { 
         stat = 1;   
         if ((p = strcasestr(p+13+5, "pages=")) != NULL)
            *pages = strtol(p+6, &tail, 10);
      }
   }

bugout:
   return stat;
}

static int parse_pjl_device_status(char *buf, int *status)
{
   char *p, *tail;
   int stat=0;

   if (buf[0] == 0)
      goto bugout;

   if ((p = strcasestr(buf, "code=")) != NULL)
   {
      *status = strtol(p+5, &tail, 10);
      stat = 1;   
   }

bugout:
   return stat;
}

static void pjl_read_thread(struct pjl_attributes *pa)
{
   enum HPMUD_RESULT stat;
   int len;
   char buf[1024];
   
   pthread_detach(pthread_self());

   DBG("starting thread %d\n", (int)pa->tid);

   pa->current_status = 10001;       /* default is ready */
   pa->eoj_pages = pa->abort = pa->done = 0;

   while (!pa->abort)
   {
      stat = get_pjl_input(pa->dd, pa->cd, buf, sizeof(buf), 0, &len);
      if (!(stat == HPMUD_R_OK || stat == HPMUD_R_IO_TIMEOUT))
         break;

      if (stat == HPMUD_R_OK)
      {
         pthread_mutex_lock(&pa->mutex);
         parse_pjl_device_status(buf, &pa->current_status);
         parse_pjl_job_end(buf, &pa->eoj_pages);
         pthread_mutex_unlock(&pa->mutex);
      }
      else
         sleep(1);
   }

   DBG("exiting thread %d abort=%d stat=%d\n", (int)pa->tid, pa->abort, stat);

   pa->done=1;
   pthread_cond_signal(&pa->done_cond);

   return;
}

/* 
 * get_printer_status
 *
 * inputs:
 *   dd - device descriptor
 *   pa - see pjl_attributes definition
 *
 * outputs:
 *   return - printer status, 1000 to 1999 = inkjet vstatus, 5000 to 5999 = hpmud error, 10000 to 55999 = pjl status code
 *    
 */
static int get_printer_status(HPMUD_DEVICE dd, HPMUD_CHANNEL cd, struct pjl_attributes *pa)
{
   char id[1024];
   char *pSf;
   int status, ver, len;
   enum HPMUD_RESULT r;

   if (pa->pjl_device)
   {
      pthread_mutex_lock(&pa->mutex);
      status = pa->current_status;
      pthread_mutex_unlock(&pa->mutex);
   }
   else
   {
      status = VSTATUS_IDLE; /* set default */
      r = hpmud_get_device_id(dd, id, sizeof(id), &len);
      if (!(r == HPMUD_R_OK || r == HPMUD_R_DEVICE_BUSY))
      {
         status = 5000+r;      /* no deviceid, return some error */
         goto bugout;
      }
   
      /* Check for valid S-field in device id string. */
      if ((pSf = strstr(id, ";S:")) == NULL)
      {
         /* No S-field, use status register instead of device id. */ 
         unsigned int bit_status;
         r = hpmud_get_device_status(dd, &bit_status);      
         if (!(r == HPMUD_R_OK || r == HPMUD_R_DEVICE_BUSY))
         {
            status = 5000+r;      /* no 8-bit status, return some error */
            goto bugout;
         }

         if (DEVICE_IS_OOP(bit_status))
            status = VSTATUS_OOPA;
         else if (DEVICE_PAPER_JAMMED(bit_status))
            status = VSTATUS_PAJM;
         else if (DEVICE_IO_TRAP(bit_status))
            status = VSTATUS_CARS;
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
               BUG("WARNING: unknown S-field version=%d\n", ver);
               pSf+=12;
               break;            
         }

         /* Extract VStatus.*/
         status = 0; 
         HEX2INT(*pSf, status);
         pSf++;
         status = status << 4;
         HEX2INT(*pSf, status);
         status += 1000;
      }
   }

bugout:
   return status;
}

static int device_discovery()
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

static int device_event(const char *dev, const char *jobid, int code, char *type, int timeout)
{
   struct sockaddr_in pin;  
   char message[512];  
   int len=0;
   int hpssd_socket=-1, hpssd_port_num=2207;

   bzero(&pin, sizeof(pin));  
   pin.sin_family = AF_INET;  
   pin.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
   pin.sin_port = htons(hpssd_port_num);  
    
   if ((hpssd_socket = socket(AF_INET, SOCK_STREAM, 0)) == -1) 
   {  
      BUG("unable to create hpssd socket %d: %m\n", hpssd_port_num);
      goto bugout;  
   }  

   if (connect(hpssd_socket, (void *)&pin, sizeof(pin)) == -1)  
   {  
      BUG("unable to connect hpssd socket %d: %m\n", hpssd_port_num);
      goto bugout;  
   }  

   if (timeout == 0)
      len = sprintf(message, "msg=Event\ndevice-uri=%s\njob-id=%s\nevent-code=%d\nevent-type=%s\n", dev, jobid, code, type);
   else
      len = sprintf(message, "msg=Event\ndevice-uri=%s\njob-id=%s\nevent-code=%d\nevent-type=%s\nretry-timeout=%d\n", 
                     dev, jobid, code, type, timeout);
 
   /* Send message with no response. */
   if (send(hpssd_socket, message, len, 0) == -1) 
   {  
      BUG("unable to send Event %s %s %d: %m\n", dev, jobid, code);
   }  

bugout:
   if (hpssd_socket >= 0)
      close(hpssd_socket);

   return 0;
}

/* Check printer status, if in an error state, loop until error condition is cleared. */
static int loop_test(HPMUD_DEVICE dd, HPMUD_CHANNEL cd, struct pjl_attributes *pa, const char *uri, const char *job)
{
   int retry=0, status;
   const char *pstate;

   while (1)
   {
      status = get_printer_status(dd, cd, pa);
      map_ipp_printer_state_reason(status, &pstate);

      if (strcmp(pstate, "none")==0)
      {
         if (retry)
         {
            /* Clear error. */
            device_event(uri, job, VSTATUS_PRNT, "event", 0);
            fputs("INFO: Printing...\n", stderr);
            fprintf(stderr, "STATE: -%s\n", pstate);
            retry=0;
         }
         break;   /* no error, done */
      }

      if (!retry)
      {
         /* Display error. */
         device_event(uri, job, status, "error", RETRY_TIMEOUT);
         fprintf(stderr, "STATE: +%s\n", pstate);
      }

      BUG("ERROR: %d %s; will retry in %d seconds...\n", status, pstate, RETRY_TIMEOUT);
      sleep(RETRY_TIMEOUT);
      retry = 1;
   }

   return 0;
}

int main(int argc, char *argv[])
{
   int fd;
   int copies;
   int len, status, cnt;
   char buf[HPMUD_BUFFER_SIZE];
   struct hpmud_model_attributes ma;
   struct pjl_attributes pa;
   HPMUD_DEVICE hd=-1;
   HPMUD_CHANNEL cd=-1;
   int n, total, retry=0, size, pages;
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
      exit (device_discovery());

   if (argc < 6 || argc > 7)
   {
      BUG("ERROR: invalid usage: device_uri job-id user title copies options [file]\n");
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
         BUG("ERROR: unable to open print file %s: %m\n", argv[6]);
         exit (1);
      }
      copies = atoi(argv[4]);
   }

   fputs("STATE: +connecting-to-device\n", stderr);

   /* Get any parameters needed for DeviceOpen. */
   hpmud_query_model(argv[0], &ma);  

   DBG("job start %s prt_mode=%d statustype=%d\n", argv[0], ma.prt_mode, ma.statustype); 

   pa.pjl_device = 0;
   if (strcasestr(argv[0], ":/net") == NULL && (ma.statustype==HPMUD_STATUSTYPE_PJL || ma.statustype==HPMUD_STATUSTYPE_PJLPML))
      pa.pjl_device = 1;

   device_event(argv[0], argv[1], EVENT_START_JOB, "event", 0);

   /* Open hp device. */
   while ((stat = hpmud_open_device(argv[0], ma.prt_mode, &hd)) != HPMUD_R_OK)
   {
       /* Display user error. */
       device_event(argv[0], argv[1], 5000+stat, "error", RETRY_TIMEOUT);

       BUG("INFO: open device failed; will retry in %d seconds...\n", RETRY_TIMEOUT);
       sleep(RETRY_TIMEOUT);
       retry = 1;
   }

   if (retry)
   {
      /* Clear user error. */
      device_event(argv[0], argv[1], VSTATUS_PRNT, "event", 0);
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
                  device_event(argv[0], argv[1], 5000+stat, "error", RETRY_TIMEOUT);
                  BUG("INFO: open print channel failed; will retry in %d seconds...\n", RETRY_TIMEOUT);
                  sleep(RETRY_TIMEOUT);
                  retry = 1;
               }

               if (retry)
               {
                  /* Clear user error. */
                  device_event(argv[0], argv[1], VSTATUS_PRNT, "event", 0);
                  retry=0;
               }          

               fputs("STATE: -connecting-to-device\n", stderr);

               if (pa.pjl_device)
               {
                  /* Enable unsolicited status. */
                  hpmud_write_channel(hd, cd, pjl_ustatus_cmd, sizeof(pjl_ustatus_cmd)-1, 5, &len);
                  pa.dd = hd;
                  pa.cd = cd;
                  pthread_mutex_init(&pa.mutex, NULL);
                  pthread_cond_init(&pa.done_cond, NULL);
                  pthread_create(&pa.tid, NULL, (void *(*)(void*))pjl_read_thread, (void *)&pa);
               }
            }

            stat = hpmud_write_channel(hd, cd, buf+total, size, EXCEPTION_TIMEOUT, &n);

            if (n != size)
            {
               /* IO error, get printer status. */
               loop_test(hd, cd, &pa, argv[0], argv[1]);
            }
            else
            {
               /* Data was sent to device successfully. */ 
               if (pa.pjl_device)
               {
                  /* Laserjets have a large data buffer, so manually check for operator intervention condition. */
                  loop_test(hd, cd, &pa, argv[0], argv[1]);
               }
            }
            total+=n;
            size-=n;
         }   /* while (size > 0) */
      }   /* while ((len = read(fd, buf, HPLIP_BUFFER_SIZE)) > 0) */
   }   /* while (copies > 0) */

   DBG("job end %s prt_mode=%d statustype=%d\n", argv[0], ma.prt_mode, ma.statustype); 

   if (pa.pjl_device)
   {
      pthread_mutex_lock(&pa.mutex);
      pa.eoj_pages=0;
      pthread_mutex_unlock(&pa.mutex);
      hpmud_write_channel(hd, cd, pjl_job_end_cmd, sizeof(pjl_job_end_cmd)-1, 5, &len);

      /* Look for job end status. */
      for (cnt=0; cnt<10; cnt++)
      {
         loop_test(hd, cd, &pa, argv[0], argv[1]);         
         pthread_mutex_lock(&pa.mutex);
         pages = pa.eoj_pages;
         pthread_mutex_unlock(&pa.mutex);
         if (pages > 0)
         {
            DBG("job end pages=%d\n", pages);
            break;
         }
         sleep(2);
      }

      hpmud_write_channel(hd, cd, pjl_ustatus_off_cmd, sizeof(pjl_ustatus_off_cmd)-1, 5, &len);

      /* Gracefully kill the pjl_read_thread. */
      pthread_mutex_lock(&pa.mutex);
      pa.abort=1;
      while (!pa.done)
         pthread_cond_wait(&pa.done_cond, &pa.mutex);
      pthread_mutex_unlock(&pa.mutex);
      pthread_cancel(pa.tid);   
      pthread_mutex_destroy(&pa.mutex);
      pthread_cond_destroy(&pa.done_cond);
   }
   else if ((ma.prt_mode != HPMUD_UNI_MODE) && (ma.statustype == HPMUD_STATUSTYPE_VSTATUS || ma.statustype == HPMUD_STATUSTYPE_SFIELD))
   {
      /* Wait for printer to receive all data before closing print channel. Otherwise data can be truncated. */
      status = get_printer_status(hd, cd, &pa);
      if (status < 5000)
      {
         /* Got valid status, wait for idle. */
         cnt=0;
         while ((status != VSTATUS_IDLE) && (status < 5000) && (cnt < 5))
         {
           sleep(2);
           status = get_printer_status(hd, cd, &pa);
           cnt++;
         } 
      }
   }
   else
   {
      /* Just use fixed delay for uni-di and laserjets without pjl. */
      sleep(8);
   }
      
   device_event(argv[0], argv[1], EVENT_END_JOB, "event", 0);
   fputs("INFO: ready to print\n", stderr);

   if (cd >= 0)
      hpmud_close_channel(hd, cd);
   if (hd >= 0)
      hpmud_close_device(hd);   
   if (fd != 0)
      close(fd);

   exit (0);
}

