/*****************************************************************************\

  hp-mkuri.c - make uri with multi-point transport driver (HPMUD)
 
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

\*****************************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <ctype.h>
#include <unistd.h>
#include "hpmud.h"

#define _STRINGIZE(x) #x
#define STRINGIZE(x) _STRINGIZE(x)
#define BUG(args...) fprintf(stderr, __FILE__ " " STRINGIZE(__LINE__) ": " args)

static int verbose;

static void usage()
{
   fprintf(stdout, "HPLIP Make URI %s\n", VERSION);
   fprintf(stdout, "(c) 2008 Copyright Hewlett-Packard Development Company, LP\n");
   fprintf(stdout, "usage: hp-mkuri -i ip [-p port]\n");
   fprintf(stdout, "usage: hp-mkuri -b busnum -d devnum\n");
   fprintf(stdout, "usage: hp-mkuri -l /dev/parportx\n");
   fprintf(stdout, "usage: hp-mkuri -o (probe)\n");
}

int main(int argc, char *argv[])
{
   char ip[HPMUD_LINE_SIZE];  /* internet address */
   char bn[HPMUD_LINE_SIZE];  /* usb bus number */
   char dn[HPMUD_LINE_SIZE];  /* usb device number */
   char pp[HPMUD_LINE_SIZE];  /* parallel port device */
   char uri[HPMUD_LINE_SIZE];
   int i, port=1, ret=1, probe=0;
   enum HPMUD_RESULT stat;
   char buf[HPMUD_LINE_SIZE*64];
   int cnt, bytes_read;

   ip[0] = bn[0] = dn[0] = pp[0] = uri[0] = 0;
   while ((i = getopt(argc, argv, "vhoi:p:b:d:l:")) != -1)
   {
      switch (i)
      {
      case 'i':
         strncpy(ip, optarg, sizeof(ip));
         break;
      case 'p':
         port = strtol(optarg, NULL, 10);
         break;
      case 'b':
         strncpy(bn, optarg, sizeof(bn));
         break;
      case 'd':
         strncpy(dn, optarg, sizeof(dn));
         break;
      case 'l':
         strncpy(pp, optarg, sizeof(pp));
         break;
      case 'o':
         probe++;
         break;
      case 'v':
         verbose++;
         break;
      case 'h':
         usage();
         exit(0);
      case '?':
         usage();
         fprintf(stderr, "unknown argument: %s\n", argv[1]);
         exit(-1);
      default:
         break;
      }
   }

   if (ip[0]==0 && (!(bn[0] && dn[0])) && pp[0]==0 && probe==0)
   {
      BUG("invalid command parameter(s)\n");
      usage();
      goto bugout;
   }   

   if (probe)
   {
      hpmud_probe_devices(HPMUD_BUS_ALL, buf, sizeof(buf), &cnt, &bytes_read);
      if (bytes_read)
         fprintf(stdout, "%s", buf);
   }

#ifdef HAVE_LIBNETSNMP
   if (ip[0])
   {
      stat = hpmud_make_net_uri(ip, port, uri, sizeof(uri), &bytes_read);
      if (stat == HPMUD_R_OK)
      {
         fprintf(stdout, "%s\n", uri);
         fprintf(stdout, "hpaio%s\n", &uri[2]);
      }
   }
#endif

   if (bn[0] && dn[0])
   {
      stat = hpmud_make_usb_uri(bn, dn, uri, sizeof(uri), &bytes_read);
      if (stat == HPMUD_R_OK)
      {
         fprintf(stdout, "%s\n", uri);
         fprintf(stdout, "hpaio%s\n", &uri[2]);
      }
   }

#ifdef HAVE_PPORT
   if (pp[0])
   {
      stat = hpmud_make_par_uri(pp, uri, sizeof(uri), &bytes_read);
      if (stat == HPMUD_R_OK)
      {
         fprintf(stdout, "%s\n", uri);
         fprintf(stdout, "hpaio%s\n", &uri[2]);
      }
   }
#endif

   ret = 0;

bugout:
   exit(ret);
}
