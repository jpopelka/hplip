/************************************************************************************\

  dime.c - Direct Internet Message Encapsulation (DIME) data consumer

  (c) 2008 Copyright Hewlett-Packard Development Company, LP

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

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <syslog.h>
#include <stdint.h>
#include <ctype.h>
#include <arpa/inet.h>
#include "hpmud.h"
#include "http.h"
#include "dime.h"

//#define DIME_DEBUG
//#define DIME_DUMP

#define _STRINGIZE(x) #x
#define STRINGIZE(x) _STRINGIZE(x)

#define BUG(args...) syslog(LOG_ERR, __FILE__ " " STRINGIZE(__LINE__) ": " args)

#ifdef DIME_DEBUG
   #define DBG(args...) syslog(LOG_INFO, __FILE__ " " STRINGIZE(__LINE__) ": " args)
   #define DBG_DUMP(data, size) sysdump((data), (size))
   #define DBG_SZ(args...) syslog(LOG_INFO, args)
#else
   #define DBG(args...)
   #define DBG_DUMP(data, size)
   #define DBG_SZ(args...)
#endif

#define EXCEPTION_TIMEOUT 45 /* seconds */

/* Dime header bit masks. */
#define DIME_MB 0x800           /* message begin */
#define DIME_ME 0x200           /* message end */

enum DIME_STATE
{
   DS_ACTIVE = 1,
   DS_EOF,
};

struct dime_header
{
   uint16_t msg;         /* VERSION:5 | MB:1 | ME:1 | CF:1 | TYPE_T:4 | reserved:4 */
   uint16_t opt_len;
   uint16_t id_len;
   uint16_t type_len;
   uint32_t data_len;   /* 4-byte aligned = (data_len + 3) & 0xfffffffc */
} __attribute__((packed));

struct dime_session
{
   enum DIME_STATE state;
   int total;
   HTTP_HANDLE http_handle;
   struct dime_header header;
   FILE *dump_fp;
};

#ifdef DIME_DEBUG
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

/* Read dime message. Return data portion only. */
static int read_msg(struct dime_session *ps, char *data, int max_size, int sec_timeout, int *bytes_read)
{
   struct dime_header header;
   int tmo=sec_timeout;   /* set initial timeout */
   enum HTTP_RESULT ret;
   int len, total, size, stat=1, act_size;
   int opt_len, id_len, type_len, data_len;
   char buf[1024], *p;
   
   /* Read dime header. */
   total = 0;
   size = sizeof(struct dime_header);
   p = (char *)&header;
   while (total < size)
   {
      if (http_read_payload(ps->http_handle, p+total, size-total, tmo, &len))
         goto bugout;
      total+=len;
   }

   /* Convert to big-endian. */
   ps->header.msg = ntohs(header.msg);
   ps->header.opt_len = ntohs(header.opt_len);
   ps->header.id_len = ntohs(header.id_len);
   ps->header.type_len = ntohs(header.type_len);
   ps->header.data_len = ntohl(header.data_len);

   DBG("dime raw counts: msg=%x opt_len=%d id_len=%d type_len=%d data_len=%d\n", ps->header.msg, 
                ps->header.opt_len, ps->header.id_len, ps->header.type_len, ps->header.data_len);

   /* Adjust counts to 4-byte boundaries. */
   opt_len = (ps->header.opt_len+3) & -4;
   id_len = (ps->header.id_len+3) & -4;
   type_len = (ps->header.type_len+3) & -4;
   data_len = (ps->header.data_len+3) & -4;

   DBG("dime adj counts: msg=%x opt_len=%d id_len=%d type_len=%d data_len=%d\n", ps->header.msg, 
                opt_len, id_len, type_len, data_len);

   /* Sanity check dime message. */ 
   if (ps->header.msg >> 11 != 1)
   {
      BUG("invalid dime version=%d\n", ps->header.msg >> 11);
      goto bugout;
   }
   
   /* Read dime message fields. */
   total = 0;
   size = opt_len + id_len + type_len;
   size = size > sizeof(buf) ? sizeof(buf) : size;
   while (total < size)
   {
      if (http_read_payload(ps->http_handle, buf+total, size-total, 1, &len) != HTTP_R_OK)
         goto bugout;
      total+=len;
   }

   if (opt_len)
   {
      DBG("options:\n");
      DBG_DUMP(buf, ps->header.opt_len);
   }
   if (id_len)
   {
      DBG("id:\n");
      DBG_DUMP(buf+ps->header.opt_len, ps->header.id_len);
   }
   if (type_len)
   {
      DBG("type:\n");
      DBG_DUMP(buf+ps->header.opt_len+ps->header.id_len, ps->header.type_len);
   }

   /* Read dime data adjusted to 4-byte boundary. */
   total = 0;
   if (data_len > max_size)
   {
      size = max_size;
      act_size = max_size;
   }
   else
   {
      size = data_len;
      act_size = ps->header.data_len;
   }
   size = data_len > max_size ? max_size : data_len;
   while (total < size)
   {
      ret = http_read_payload(ps->http_handle, data+total, size-total, tmo, &len);
      if (!(ret == HTTP_R_OK || ret == HTTP_R_EOF))
         goto bugout;
      total+=len;
//      tmo=1;
      if (ret == HTTP_R_EOF)
         break;    /* done */
   }
   *bytes_read = act_size;    /* return actual data size */
   ps->total += act_size;
   stat = 0;

bugout:
   return stat;
}

/*
 * Dime_open must be called for each dime encoded document. 
 * Each document is consumed over HTTP/1.1 chunked data stream. 
 */
enum DIME_RESULT __attribute__ ((visibility ("hidden"))) dime_open(HTTP_HANDLE http_handle, DIME_HANDLE *handle)
{
   struct dime_session *ps;
   enum DIME_RESULT stat = DIME_R_IO_ERROR;
   char buf[1024];
   int len, tmo = EXCEPTION_TIMEOUT;

   DBG("dime_open() http_handle=%p handle=%p\n", http_handle, handle);

   *handle = NULL;

   if ((ps = malloc(sizeof(struct dime_session))) == NULL)
   {
      BUG("malloc failed: %m\n");
      return DIME_R_MALLOC_ERROR;
   }
   memset(ps, 0, sizeof(struct dime_session));
   ps->http_handle = http_handle;

   /* Read HTTP/1.1 dime header. */
   if (http_read_header(ps->http_handle, buf, sizeof(buf), tmo, &len) != HTTP_R_OK)
      goto bugout; 

   /* First dime message is the soap reference, eat it... */      
   if (read_msg(ps, buf, sizeof(buf), tmo, &len))
      goto bugout;

   /* Check for message begin. */
   if (!(ps->header.msg & DIME_MB))
   {
      BUG("invalid dime message=%x\n", ps->header.msg);
      goto bugout;
   }

   ps->state = DS_ACTIVE;
   ps->total = 0;
   *handle = ps;
   stat = DIME_R_OK;

#ifdef DIME_DUMP
   /* For hpraw use 'display -size 637x876 -depth 8 rgb:/tmp/dump.out'. See xsane for width x height. */
   char sz[] = "/tmp/dump.out";      
   if((ps->dump_fp = fopen(sz, "w")) == NULL) 
      BUG("unable to open %s: %m\n", sz);
#endif

bugout:
   if (stat != DIME_R_OK)
      free(ps);
   return stat;
}

/* Dime_close must be called at the end of the dime encoded document. */
enum DIME_RESULT __attribute__ ((visibility ("hidden"))) dime_close(DIME_HANDLE handle)
{
   struct dime_session *ps = (struct dime_session *)handle;
   DBG("dime_close() handle=%p total=%d\n", handle, ps->total);
#ifdef DIME_DUMP
   if (ps->dump_fp)
      fclose(ps->dump_fp);
#endif
   free(ps);
   return DIME_R_OK;
}

/* Read dime data from HTTP/1.1 chunked data stream. Returns dime data until end of dime document. */
enum DIME_RESULT __attribute__ ((visibility ("hidden"))) dime_read(DIME_HANDLE handle, void *data, int max_size, int sec_timeout, int *bytes_read)
{
   struct dime_session *ps = (struct dime_session *)handle;
   enum DIME_RESULT stat = DIME_R_IO_ERROR;
   int len;

   DBG("dime_read() handle=%p data=%p max_size=%d sectime=%d\n", handle, data, max_size, sec_timeout);

   *bytes_read = 0;

   if (ps->state == DS_EOF)
   {
      stat = DIME_R_EOF;
   }
   else
   {
      if (read_msg(ps, data, max_size, sec_timeout, &len))
	 goto bugout;

      *bytes_read = len;

      if (ps->header.msg & DIME_ME)
	 ps->state = DS_EOF;     /* done with dime document, next dime_read will be EOF */ 

      stat = DIME_R_OK;
   }

#ifdef DIME_DUMP
   if (ps->dump_fp)
      fwrite(data, 1, *bytes_read, ps->dump_fp);
#endif

   DBG("-dime_read() handle=%p data=%p bytes_read=%d max_size=%d status=%d\n", handle, data, *bytes_read, max_size, stat);
 
bugout:
   return stat;
};





